import boto3
import config
import io
import os
import re
import sys
import json
import glob
import calendar
import time
import datetime as dt
import pandas as pd
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, RequestError
from requests_aws4auth import AWS4Auth
from utility import create_policies_in_oss, interactive_sleep
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
sts_client = boto3.client("sts")
s3_client = boto3.client("s3")
aos_client = boto3.session.Session().client("opensearch") # opensearch, opensearchserverless
bedrock_agent_client = boto3.session.Session().client("bedrock-agent", region_name="us-west-2")
bedrock_client = boto3.client("bedrock-runtime")
class AWS:
    def __init__(self):
        self.account_id = sts_client.get_caller_identity()["Account"]
        self.credentials = boto3.Session().get_credentials()
        self.Oregon = boto3.session.Session().region_name
        self.Tokyo = "ap-northeast-1"
        self.serverless = "aoss"
        self.provisioned = "es"
        # self.bedrock_execution_role = None
        self.bucket_name = f"bedrock-kb-{self.Oregon}-{self.account_id}"
        self.collection_name = f"bedrock-sample-rag-{config.suffix}"
        self.index_name = f"bedrock-sample-index-{config.suffix}"
        self.host = ""
    def upload_to_s3(self, path, bn: str):  # Uploads file to s3
        s3_client = boto3.client("s3")
        for root, dirs, files in os.walk(path):
            for file in files:
                print(file)
                s3_client.upload_file(os.path.join(root, file), bn, file)
        config.logging.info("Upload Files Finished!")
    def update_package(self, package_id, bucket_name, s3_key):  # Updates the package in OpenSearch Service
        print(package_id, bucket_name, s3_key)
        response = aos_client.update_package(
            PackageID=package_id,
            PackageSource={
                "S3BucketName": bucket_name,
                "S3Key": s3_key
            }
        )
        print(response)
    def associate_package(self, package_id, domain_name):  # Associates the package to the domain
        response = aos_client.associate_package(
            PackageID=package_id,
            DomainName=domain_name
        )
        print(response)
        print("Associating...")
    def wait_for_update(self, domain_name, package_id):  # Waits for the package to be updated
        response = aos_client.list_packages_for_domain(DomainName=domain_name)
        package_details = response["DomainPackageDetailsList"]
        for package in package_details:
            if package["PackageID"] == package_id:
                status = package["DomainPackageStatus"]
                if status == "ACTIVE":
                    print("Association successful.")
                    return
                elif status == "ASSOCIATION_FAILED":
                    sys.exit("Association failed. Please try again.")
                else:
                    time.sleep(10)  # Wait 10 seconds before rechecking the status
                    self.wait_for_update(domain_name, package_id)
    def generate_bucket_name(self, bn: str):
        self.bucket_name = bn
        config.logging.info(f"Bucket Name = {self.bucket_name}")
    def generate_collection_name(self, cn: str):
        self.collection_name = cn
        config.logging.info(f"Collection Name = {self.collection_name}")
    def generate_index_name(self, idn: str):
        self.index_name = idn
        config.logging.info(f"Index Name = {self.index_name}")
    def create_s3_bucket(self):
        try:
            s3_client.head_bucket(Bucket=self.bucket_name)
            config.logging.info(f"Bucket {self.bucket_name} Exists")
        except ClientError as e:
            s3_bucket = s3_client.create_bucket(
                Bucket=self.bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.Oregon}
            )
            config.logging.info(f"Creating Bucket {self.bucket_name} Finished!")
    def create_oss_policies(self):
        # self.bedrock_execution_role = create_bedrock_execution_role(bucket_name=self.bucket_name)
        # bedrock_kb_execution_role_arn = self.bedrock_execution_role["Role"]["Arn"]
        encryption_policy, network_policy, access_policy = create_policies_in_oss(
            vector_store_name=self.collection_name,
            aoss_client=aos_client,
            arn=config.arn
            # bedrock_kb_execution_role_arn=bedrock_kb_execution_role_arn
        )
        config.logging.info("Policy Successfully Created!")
    def create_oss_collection(self):
        collection = aos_client.create_collection(name=self.collection_name, type="VECTORSEARCH")
        config.pp.pprint(collection)
        collection_id = collection["createCollectionDetail"]["id"]
        self.host = collection_id + '.' + self.Oregon + ".aoss.amazonaws.com"
        config.logging.info(f"host = {self.host}")
        response = aos_client.batch_get_collection(names=[self.collection_name])
        while (response["collectionDetails"][0]["status"]) == "CREATING":
            config.logging.info("Creating Collection...")
            interactive_sleep(30)
            response = aos_client.batch_get_collection(names=[self.collection_name])
        config.logging.info(f"Creating Collection {self.collection_name} Finished!")
        config.pp.pprint(response["collectionDetails"])
        '''
        try:
            create_oss_policy_attach_bedrock_execution_role(collection_id=collection_id, bedrock_kb_execution_role=self.bedrock_execution_role)
            interactive_sleep(60)
        except Exception as e:
            config.logging.info("Policy already exists")
            config.pp.pprint(e)
        config.logging.info("Attach Bedrock Execution Role Successful!")
        '''
    def create_ops_index(self, host: str, menu, deploy: str):
        if deploy == "serverless":
            awsauth = auth = AWSV4SignerAuth(self.credentials, self.Oregon, self.serverless)
        elif deploy == "provisioned":
            awsauth = AWS4Auth(self.credentials.access_key, self.credentials.secret_key, self.Tokyo, self.provisioned) # session_token=self.credentials.token
        ops_client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=600
        )
        try:
            if deploy == "serverless":
                # response = ops_client.indices.create(index=config.index_name_serverless, body=json.dumps(menu))
                response = ops_client.indices.create(index=config.index_name_serverless, body=menu, ignore=400)
                config.logging.info("Creating Index...")
                config.pp.pprint(response)
                interactive_sleep(60)
                config.logging.info(f"Creating Index {config.index_name_serverless} Finished!")
            elif deploy == "provisioned":
                # response = ops_client.indices.create(index=config.index_name_provisioned, body=json.dumps(menu))
                response = ops_client.indices.create(index=config.index_name_provisioned, body=menu, ignore=400)
                config.logging.info("Creating Index...")
                config.pp.pprint(response)
                config.logging.info(f"Creating Index {config.index_name_provisioned} Finished!")
        except RequestError as e:
            # ops_client.indices.delete(index=index_name) # you can delete the index if its already exists
            print(f"Error while trying to create the index, with error {e.error}\nyou may unmark the delete above to delete, and recreate the index")
    def delete_ops_index_file(self, host: str, id: str, deploy: str):
        if deploy == "serverless":
            awsauth = auth = AWSV4SignerAuth(self.credentials, self.Oregon, self.serverless)
        elif deploy == "provisioned":
            awsauth = AWS4Auth(self.credentials.access_key, self.credentials.secret_key, self.Tokyo, self.provisioned) # session_token=self.credentials.token
        ops_client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=600
        )
        try:
            if deploy == "serverless":
                response = ops_client.delete(index=config.index_name_serverless, id=id)
            elif deploy == "provisioned":
                response = ops_client.delete(index=config.index_name_provisioned, id=id)
            config.logging.info(f"Deleting file({id}) Of Index...")
            config.pp.pprint(response)
        except RequestError as e:
            print(f"Error while trying to delete the index, with error {e.error}\nmay be no files found for this index")
    def embedding(self, text, lang):
        body = {
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        }
        try:
            response = bedrock_client.invoke_model(body=json.dumps(body), modelId=config.model_eb)
            vectorJson = json.loads(response["body"].read() if lang == "en" else response["body"].read().decode("utf8"))
            return vectorJson
        except Exception as e:
            config.logging.info("Couldn't invoke " + config.model_eb)
            print(e)
            raise
    def create_paragraph_ingest(self, filename: str, news: dict, host: str, idn: str, deploy: str, lang: str):
        if deploy == "serverless":
            awsauth = auth = AWSV4SignerAuth(self.credentials, self.Oregon, self.serverless)
        elif deploy == "provisioned":
            awsauth = AWS4Auth(self.credentials.access_key, self.credentials.secret_key, self.Tokyo, self.provisioned)  # session_token=self.credentials.token
        ops_client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=600
        )
        count = 0
        content = {}
        content.update({"sourcefile": filename})
        content.update({"sourcetype": news["sourcetype"]})
        content.update({"sourcetype_vector": self.embedding(news["sourcetype"], lang)["embedding"]})
        content.update({"datepublish": news["datepublish"]})
        content.update({"subject": news["subject"]})
        content.update({"subject_vector": self.embedding(news["subject"], lang)["embedding"]})
        if news["keyword"] != "":
            content.update({"keyword": news["keyword"] if lang == "en" else f"{news['keyword']},{news['datepublish'].split('-', 2)[0]}年{news['datepublish'].split('-', 2)[1]}月{news['datepublish'].split('-', 2)[2]}日"})
            content.update({"keyword_vector": self.embedding(news["keyword"], lang)["embedding"]})
        else:
            content.update({"keyword": news["keyword"] if lang == "en" else f"{news['keyword']},{news['datepublish'].split('-', 2)[0]}年{news['datepublish'].split('-', 2)[1]}月{news['datepublish'].split('-', 2)[2]}日"})
        content.update({"reporter": news["reporter"]})
        news["reporter"] and content.update({"reporter_vector": self.embedding(news["reporter"], lang)["embedding"]})
        for paragraph in split_text(news["body"], lang):
            count += 1
            paragraph_content = content.copy()
            paragraph_content.update({"body": paragraph})
            paragraph_content.update({"body_vector": self.embedding(paragraph, lang)["embedding"]})
            paragraph_content.update({"news_key": "a{}-{}".format(news["news_key"], count) if lang == "en" else "{}-{}".format(news["news_key"], count)})
            sorted_content = dict(sorted(paragraph_content.items(), key=lambda item: config.custom_field.index(item[0])))
            del paragraph_content
            if deploy == "serverless":
                resp = ops_client.index(index=idn, body=sorted_content)
                print(resp)
            elif deploy == "provisioned":
                resp = ops_client.index(index=idn, body=sorted_content, id=sorted_content["news_key"])
                print(resp)
            del sorted_content
        del content
    def index_search(self, query, host: str, idn: str, deploy: str):
        if deploy == "serverless":
            awsauth = auth = AWSV4SignerAuth(self.credentials, self.Oregon, self.serverless)
        elif deploy == "provisioned":
            awsauth = AWS4Auth(self.credentials.access_key, self.credentials.secret_key, self.Tokyo, self.provisioned) # session_token=self.credentials.token
        ops_client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=600
        )
        response = ops_client.search(
            body=query,
            index=idn
        )
        return response
    def invoke_sonnect(self, sysp, usrp):
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "system": sysp,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": usrp
                            }
                        ]
                    }
                ]
            }
            response = bedrock_client.invoke_model_with_response_stream(modelId=config.model_sn, body=json.dumps(body))
            buffer = io.StringIO()
            for event in response.get("body"):
                chunk = json.loads(event["chunk"]["bytes"])
                if (chunk["type"] == "content_block_delta"):
                    buffer.write(chunk["delta"]["text"])
                    # print(chunk["delta"]["text"], end='')
                elif (chunk["type"] == "message_start"):
                    inputTokens = chunk["message"]["usage"]["input_tokens"]
                elif (chunk["type"] == "message_stop"):
                    outputTokens = chunk["amazon-bedrock-invocationMetrics"]["outputTokenCount"]
            return buffer.getvalue()
        except Exception as error:
            raise error
    def sonnect_streaming(self, results, sysmg, subject, other_subject, image_dict, condition, final_question):
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "system": sysmg,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": final_question
                            }
                        ]
                    }
                ]
            }
            response = bedrock_client.invoke_model_with_response_stream(modelId=config.model_sn, body=json.dumps(body))
            buffer = io.StringIO()
            a = ""
            for event in response.get("body"):
                chunk = json.loads(event["chunk"]["bytes"])
                if chunk["type"] == "content_block_delta":
                    a += chunk["delta"]["text"]
                    buffer.write(chunk["delta"]["text"])
                    response = {"response": chunk["delta"]["text"]}
                    response = json.dumps(response)
                    yield f"data: {response}\n\n"
                elif chunk["type"] == "message_start":
                    inputTokens = chunk["message"]["usage"]["input_tokens"]
                elif chunk["type"] == "message_stop":
                    outputTokens = chunk["amazon-bedrock-invocationMetrics"]["outputTokenCount"]
            print(a)
            data_info = {"data_points": results, "subject": subject, "other_subject": other_subject, "image_dict": image_dict, "condition": condition, "query_text": final_question}
            data_info = json.dumps(data_info)
            # time.sleep(0.03)
            yield f"data: !start!\n\n"
            yield f"data: {data_info}\n\n"
        except Exception as error:
            raise error

def s3():
    aws = AWS()
    aws.generate_bucket_name("")
    aws.create_s3_bucket() # bucket
    aws.upload_to_s3(config.upload_path, aws.bucket_name)
def oss_policies_collection():
    aws = AWS()
    aws.generate_collection_name("dt-collection")
    aws.create_oss_policies() # collection
    aws.create_oss_collection() # collection
def ops_index(deploy):
    aws = AWS()
    if deploy == "serverless":
        aws.create_ops_index(config.host_serverless, config.field_menu, deploy)
    elif deploy == "provisioned":
        aws.create_ops_index(config.host_provisioned, config.field_menu, deploy)
def split_text(text, lang):
    if lang == "en":
        SENTENCE_ENDINGS = [",", "!", "?"]
        WORDS_BREAKS = [";", ":", "(", ")", "[", "]", "{", "}", "\t", "\n"]
    elif lang == "ch":
        SENTENCE_ENDINGS = ["。", "!", "?"]
        WORDS_BREAKS = ["，", "；", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
    all_text = text
    length = len(all_text)
    start = 0
    end = length
    if length > 1000:
        MAX_SECTION_LENGTH = int(length / (round(length / 1000)))
        SPLIT_LIMIT = 100
        while start < length:
            last_word = -1
            end = start + MAX_SECTION_LENGTH

            if end > length:
                end = length
            else:
                while end < length and (end - start - MAX_SECTION_LENGTH) < SPLIT_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                    if all_text[end] in WORDS_BREAKS:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                    end = last_word

            last_word = -1
            while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SPLIT_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
                if all_text[start] in WORDS_BREAKS:
                    last_word = start
                start -= 1
            if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                start = last_word

            section_text = all_text[start:end]
            section_text_len = len(section_text)
            start += section_text_len
            yield (section_text)
        del all_text
        del start
        del end
        del section_text_len
        del length
    else:
        MAX_SECTION_LENGTH = 1000
        SPLIT_LIMIT = 100
        while start < length:
            last_word = -1
            end = start + MAX_SECTION_LENGTH

            if end > length:
                end = length
            else:
                while end < length and (end - start - MAX_SECTION_LENGTH) < SPLIT_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                    if all_text[end] in WORDS_BREAKS:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                    end = last_word

            last_word = -1
            while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SPLIT_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
                if all_text[start] in WORDS_BREAKS:
                    last_word = start
                start -= 1
            if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                start = last_word

            section_text = all_text[start:end]
            section_text_len = len(section_text)
            start += section_text_len
            yield (section_text)
        del all_text
        del start
        del end
        del section_text_len
        del length
def get_news_text(filename, lang):
    if lang == "en":
        with open(filename, "r", errors="ignore") as f:
            json_data = json.load(f)["datalist"]
        json_data["subject"] = BeautifulSoup(json_data["subject"], "html.parser").get_text()
        json_data["body"] = BeautifulSoup(json_data["body"], "html.parser").get_text()
    elif lang == "ch":
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            json_data = json.load(f)["datelist"]
        json_data["subject"] = BeautifulSoup(BeautifulSoup(json_data["subject"], "html.parser").get_text(), "html.parser").get_text()
        json_data["body"] = BeautifulSoup(BeautifulSoup(json_data["body"], "html.parser").get_text(), "html.parser").get_text()
        json_data["news_key"] = json_data["news_key"].lower()
        # json_data["datepublish"] = datetime.strptime(json_data["datepublish"], "%Y-%m-%d")
    json_data["keyword"] = "" if json_data["keyword"] is None else json_data["keyword"].replace("\"", "")
    json_data["reporter"] = json_data.get("reporter", "")
    json_data.update({"sourcetype": "news"})
    return json_data
def count_paragraph(news: dict, lang: str):
    paragraphs = list(split_text(news["body"], lang))
    count = len(paragraphs)
    del paragraphs
    return count
def delete_news_by_id(files, deploy: str, lang: str):
    aws = AWS()
    if deploy == "serverless":
        for filename in glob.glob(files):
            newskey = "a" + os.path.basename(filename).split("-")[3].split(".")[0]
            print(newskey)
            config.query_file_id["query"]["match"]["news_key"] = newskey
            result = aws.index_search(config.query_file_id, config.host_serverless, config.index_name_serverless, deploy)
            print(result)
            for r in result["hits"]["hits"]:
                if r["_source"]["news_key"].find(newskey) != -1:
                    print(r["_id"])
                    aws.delete_ops_index_file(config.host_serverless, r["_id"], deploy)
    elif deploy == "provisioned":
        for filename in glob.glob(files):
            all_content = get_news_text(filename, lang)
            totalparagraph = count_paragraph(all_content, lang)
            for p in range(1, totalparagraph + 1):
                aws.delete_ops_index_file(config.host_provisioned, "{}{}-{}".format("a" if lang == "en" else "", all_content["news_key"], p), deploy)
def news_ingest(files, deploy, lang):
    aws = AWS()
    if deploy == "serverless":
        for filename in glob.glob(files):
            print(str(filename))
            all_content = get_news_text(filename, lang)
            aws.create_paragraph_ingest(os.path.basename(filename), all_content, config.host_serverless, config.index_name_serverless, deploy, lang)
            os.remove(filename)
    elif deploy == "provisioned":
        for filename in glob.glob(files):
            print(str(filename))
            all_content = get_news_text(filename, lang)
            aws.create_paragraph_ingest(os.path.basename(filename), all_content, config.host_provisioned, config.index_name_provisioned, deploy, lang)
            os.remove(filename)
def update_news_serverless():
    files = r"Z:\資訊發展中心\09.專案\English Consult AI\update_daily\*"
    delete_news_by_id(files, "serverless", "en")
    news_ingest(files, "serverless", "en")
def update_news_provisioned():
    files = r"D:\Downloads\article\*"
    delete_news_by_id(files, "provisioned", "ch")
    news_ingest(files, "provisioned", "ch")
def get_first_and_last_day_months_ago(months):
    months_ago = datetime.now()-relativedelta(months=months)
    year = months_ago.year
    month = months_ago.month
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    first_day = datetime.strftime(first_day, "%Y-%m-%d")
    last_day = datetime.strftime(last_day, "%Y-%m-%d")
    del months_ago, year, month
    return first_day, last_day
def get_first_and_last_day_lastweek_list():
    year, week_num,day_of_week = dt.date.today().isocalendar()
    lastweek_list = []
    for i in range(7):
        lastweek_list.append(str(dt.date.today()-timedelta(days=i+day_of_week+1)))
    del year, week_num, day_of_week
    return min(lastweek_list), max(lastweek_list)
def get_first_and_last_day_thissweek_list():
    year, week_num, day_of_week = dt.date.today().isocalendar()
    thisweek_list = []
    for i in range(day_of_week):
        thisweek_list.append(str(dt.date.today()-timedelta(days=i)))
    del year, week_num, day_of_week
    return min(thisweek_list), max(thisweek_list)
def set_range_time(start_time, end_time):
    config.range_time["range"]["datepublish"]["gte"] = start_time
    config.range_time["range"]["datepublish"]["lte"] = end_time
def set_query_body(q_vector):
    config.query_body["query"]["bool"]["must"].append(config.range_time)
    config.query_body["query"]["bool"]["should"][0]["function_score"]["query"]["knn"]["subject_vector"]["vector"] = q_vector
    config.query_body["query"]["bool"]["should"][1]["function_score"]["query"]["knn"]["keyword_vector"]["vector"] = q_vector
    config.query_body["query"]["bool"]["should"][2]["function_score"]["query"]["knn"]["body_vector"]["vector"] = q_vector
def set_query_body_both(search_question, q_vector):
    config.query_body_both["query"]["bool"]["must"].append(config.range_time)
    config.query_body_both["query"]["bool"]["should"][0]["function_score"]["query"]["match"]["subject"]["query"] = search_question
    config.query_body_both["query"]["bool"]["should"][1]["function_score"]["query"]["knn"]["subject_vector"]["vector"] = q_vector
    config.query_body_both["query"]["bool"]["should"][2]["function_score"]["query"]["knn"]["keyword_vector"]["vector"] = q_vector
    config.query_body_both["query"]["bool"]["should"][3]["function_score"]["query"]["knn"]["body_vector"]["vector"] = q_vector
def set_query_body_rescore(search_question, q_vector):
    config.query_body_rescore["query"]["bool"]["must"].append(config.range_time)
    config.query_body_rescore["query"]["bool"]["should"][0]["bool"]["must"][0]["function_score"]["query"]["match"]["subject"]["query"] = search_question
    config.query_body_rescore["query"]["bool"]["should"][1]["function_score"]["query"]["knn"]["subject_vector"]["vector"] = q_vector
    config.query_body_rescore["query"]["bool"]["should"][2]["function_score"]["query"]["knn"]["keyword_vector"]["vector"] = q_vector
    config.query_body_rescore["query"]["bool"]["should"][3]["function_score"]["query"]["knn"]["body_vector"]["vector"] = q_vector
    config.query_body_rescore["rescore"]["query"]["rescore_query"]["match"]["subject"]["query"] = search_question
def filter_dataframe(result_body):
    data = []
    for hit in result_body["hits"]["hits"]:
        data.append({
            "score": hit["_score"],
            "subject": hit["_source"]["subject"],
            "datepublish": hit["_source"]["datepublish"],
            "keyword": hit["_source"]["keyword"],
            "body": hit["_source"]["body"],
            "reporter": hit["_source"]["reporter"],
            "news_key": hit["_source"]["news_key"],
            "sourcefile": hit["_source"]["sourcefile"],
            "sourcetype": hit["_source"]["sourcetype"]
        })
    df = pd.DataFrame(data)
    dataframe = df[df["score"] >= config.filter_socre].reset_index(drop=True)
    dataframe = dataframe[:10]
    del data, df
    return dataframe
def generate_subject(k, file_key_words, authorized_dict):
    subject = []
    k = k[:5].reset_index(drop=True)
    for i in range(len(k["news_key"])):
        if "col" in k["news_key"][i]:
            col_key = k["news_key"][i].split("-")[0]
            col_key = col_key.split("_")[1]
            subject.append({"news_key": col_key, "filename": "".format(col_key), "title": k["subject"][i],"type": "news"})
            del col_key
        elif "external" in k["news_key"][i]:
            subject.append({"news_key": k["news_key"][i].split("-")[0], "filename": k["reporter"][i], "title": k["subject"][i],"type": "external"})
        elif "statistics" in k["news_key"][i]:
            subject.append({"news_key": k["news_key"][i].split("-")[0], "filename": "".format(re.search('\(([^)]+)', k["A"][i]).group(1),re.search('\(([^)]+)',k["B"][i]).group(1),re.search('\(([^)]+)', k["C"][i]).group(1),k["D"][i],str(int(k["duration"][i].split("~")[1][:4])-5)+k["duration"][i].split("~")[1][4:],k["duration"][i].split("~")[1],re.search('\(([^)]+)', k["E"][i]).group(1)), "title": k["subject"][i]+"("+k["D"][i]+")","type": "statistics"})
        elif k["news_key"][i].count("-") == 1 and not any(j in k["news_key"][i] for j in file_key_words):
            subject.append({"news_key": k["news_key"][i].split("-")[0], "filename": "".format(k["news_key"][i].split("-")[0]), "title": k["subject"][i],"type": "news"})
        elif k["news_key"][i].count("-") > 1 and not any(j in k["news_key"][i] for j in file_key_words):
            if k["news_key"][i].count("-") == 4:
                subject.append({"news_key": "-".join(k["news_key"][i].split("-")[:-1]), "filename": "".format("-".join(k["news_key"][i].split("-")[:-3]), k["news_key"][i].split("-")[-2]), "title": k["subject"][i]+"#"+k["news_key"][i].split("-")[-2]+"("+authorized_dict[k["sourcefile"][i]]+")","type": "research"})
            else:
                subject.append({"news_key": "-".join(k["news_key"][i].split("-")[:-1]), "filename": "".format("-".join(k["news_key"][i].split("-")[:-1])), "title": k["subject"][i]+"("+authorized_dict[k["sourcefile"][i]]+")","type": "research"})
        else:
            pass
    subject = pd.DataFrame(subject)
    subject = subject.drop_duplicates(subset = ["title"]).reset_index(drop=True)
    subject = subject.to_dict("records")
    return subject
def append_to_log(file_path, lists):
    with open(file_path, "a", encoding="utf-8") as file:
        for line in lists:
            file.write(line + "\n")