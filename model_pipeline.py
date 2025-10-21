from preprocessing import AWS, get_first_and_last_day_months_ago, get_first_and_last_day_lastweek_list, get_first_and_last_day_thissweek_list, set_range_time, set_query_body, set_query_body_both, set_query_body_rescore, filter_dataframe, generate_subject, append_to_log
from langchain.prompts import PromptTemplate
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from typing import Any, Sequence
import pandas as pd
import config
import re

def run(history: Sequence[dict[str, str]], tk: str):
    key_word = ["sorry","don't know","do not know"]
    file_key_words = []
    aws = AWS()
    # for i in range(len(history)):
    #     print(f"Q{i+1}: " + history[i]["user"])
    one_month_ago_first_day, one_month_ago_last_day = get_first_and_last_day_months_ago(months=1)
    three_month_ago_first_day, three_month_ago_last_day = get_first_and_last_day_months_ago(months=3)
    lastweek_first_day, lastweek_last_day = get_first_and_last_day_lastweek_list()
    thisweek_first_day, thisweek_last_day = get_first_and_last_day_thissweek_list()
    sysmg = config.search_query_chat_conversation.format(year=datetime.strftime(datetime.today(), "%Y-%m-%d"), start=one_month_ago_first_day, end=one_month_ago_last_day, start2=three_month_ago_first_day, end2=three_month_ago_last_day, start3=lastweek_first_day, end3=lastweek_last_day, start4=datetime.strftime(datetime.now()-relativedelta(months=3), "%Y-%m-%d"), end4=datetime.strftime(datetime.today(), "%Y-%m-%d"), start5=datetime.strftime(datetime.now()-relativedelta(months=4), "%Y-%m-%d"), end5=datetime.strftime(datetime.today(), "%Y-%m-%d"), start6=datetime.strftime(datetime.today()-timedelta(days=14), "%Y-%m-%d"), end6=datetime.strftime(datetime.today(), "%Y-%m-%d"), start7=datetime.strftime(datetime.now()-relativedelta(months=12), "%Y"), end7=datetime.strftime(datetime.now()-relativedelta(months=12), "%Y"), start8=datetime.strftime(datetime.today(), "%Y-%m-%d"), end8=datetime.strftime(datetime.today(), "%Y-%m-%d"), start9=thisweek_first_day, end9=thisweek_last_day, start10=datetime.strftime(datetime.today()-timedelta(days=30), "%Y-%m-%d"), end10=datetime.strftime(datetime.today(), "%Y-%m-%d"))
    if len(history) >= 1:
        conversation = ""
        for h in history[:-1]:
            conversation += "question: " + h.get("user") + ",\n"
            if h.get("bot"):
                conversation += "answer: " + h.get("bot") + ",\n"
        conversation += "last question: " + history[-1]["user"] + "\n"
        final_question = aws.invoke_sonnect(sysmg, conversation)
        del conversation
    else:
        final_question = aws.invoke_sonnect(sysmg, history[-1]["user"])

    if final_question.find("from") != -1 and final_question.find("to") != -1:
        search_question = final_question[:final_question.find("from")]
        q_vector = aws.embedding(search_question, "en")["embedding"]
        flag = True
        config.range_time["range"]["datepublish"]["gte"] = final_question[final_question.find("from"):].split("-", 1)[0][-4:] + "-" + final_question[final_question.find("from"):].split("-", 1)[1][:5]
        config.range_time["range"]["datepublish"]["lte"] = final_question[final_question.find("to"):].split("-", 1)[0][-4:] + "-" + final_question[final_question.find("to"):].split("-", 1)[1][:5]
        config.query_body["query"]["bool"]["must"].append(config.range_time) # = [config.range_time]
        # config.query_body["query"]["bool"]["must"][0]["multi_match"]["query"] = search_question
        # config.query_body["query"]["bool"]["should"][0]["multi_match"]["query"] = search_question
        config.query_body["query"]["bool"]["should"][0]["function_score"]["query"]["knn"]["subject_vector"]["vector"] = q_vector
        config.query_body["query"]["bool"]["should"][1]["function_score"]["query"]["knn"]["keyword_vector"]["vector"] = q_vector
        config.query_body["query"]["bool"]["should"][2]["function_score"]["query"]["knn"]["body_vector"]["vector"] = q_vector
        append_to_log("./consult_log.txt", ["[{}] Start search (from ~ to) time range.".format(datetime.today().strftime("%H:%M:%S"))])
    else:
        search_question = final_question
        q_vector = aws.embedding(search_question, "en")["embedding"]
        flag = False
        config.range_time["range"]["datepublish"]["gte"] = datetime.strftime(datetime.now()-timedelta(days=180),'%Y-%m-%d')
        config.range_time["range"]["datepublish"]["lte"] = datetime.strftime(datetime.now(),'%Y-%m-%d')
        config.query_body["query"]["bool"]["must"].append(config.range_time) # = [config.range_time]
        # config.query_body["query"]["bool"]["must"][0]["multi_match"]["query"] = search_question
        # config.query_body["query"]["bool"]["should"][0]["multi_match"]["query"] = search_question
        config.query_body["query"]["bool"]["should"][0]["function_score"]["query"]["knn"]["subject_vector"]["vector"] = q_vector
        config.query_body["query"]["bool"]["should"][1]["function_score"]["query"]["knn"]["keyword_vector"]["vector"] = q_vector
        config.query_body["query"]["bool"]["should"][2]["function_score"]["query"]["knn"]["body_vector"]["vector"] = q_vector
        append_to_log("./consult_log.txt", ["[{}] Start search (half year ~ current) time range.".format(datetime.today().strftime("%H:%M:%S"))])
    r = aws.index_search(config.query_body, config.host_serverless, config.index_name_serverless, "serverless")
    r = pd.DataFrame(list(r["hits"]["hits"]))
    r = pd.DataFrame(list(r["_source"]))
    append_to_log("./consult_log.txt", ["[{}] final question = {}".format(datetime.today().strftime("%H:%M:%S"), final_question)])
    append_to_log("./consult_log.txt", ["[{}] search question = {}".format(datetime.today().strftime("%H:%M:%S"), search_question)])

    msg_to_display = ""
    if not r.empty:
#         for i in range(len(r["news_key"])):
#             msg_to_display = msg_to_display + r["body"][i] + "\\n"
        append_to_log("./consult_log.txt", ["[{}] get relavent news through semantic search end.".format(datetime.today().strftime("%H:%M:%S"))])
        msg_to_display = r.to_json(orient="records", force_ascii=False)
        subject = generate_subject(r, file_key_words, authorized_dict = [])
        sysmg = f"{config.system_message_chat_conversation_withsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}\n\nSources:\n{msg_to_display}"
        append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on relavent news start.".format(datetime.today().strftime("%H:%M:%S"))])
        answer = aws.invoke_sonnect(sysmg, final_question)

        if any(i in answer for i in key_word) and flag is False:
            append_to_log("./consult_log.txt", ["[{}] Claude3 don't know based on (half year ~ current) relavent news.".format(datetime.today().strftime("%H:%M:%S"))])
            config.range_time["range"]["datepublish"]["gte"] = datetime.strftime(datetime.now()-timedelta(days=1095), '%Y-%m-%d')
            config.range_time["range"]["datepublish"]["lte"] = datetime.strftime(datetime.now(),'%Y-%m-%d')
            config.query_body["query"]["bool"]["must"].append(config.range_time) # = [config.range_time]
            # config.query_body["query"]["bool"]["must"][0]["multi_match"]["query"] = search_question
            # config.query_body["query"]["bool"]["should"][0]["multi_match"]["query"] = search_question
            config.query_body["query"]["bool"]["should"][0]["function_score"]["query"]["knn"]["subject_vector"]["vector"] = q_vector
            config.query_body["query"]["bool"]["should"][1]["function_score"]["query"]["knn"]["keyword_vector"]["vector"] = q_vector
            config.query_body["query"]["bool"]["should"][2]["function_score"]["query"]["knn"]["body_vector"]["vector"] = q_vector
            append_to_log("./consult_log.txt", ["[{}] Start search (three years ~ current) time range.".format(datetime.today().strftime("%H:%M:%S"))])
            r = aws.index_search(config.query_body, config.host_serverless, config.index_name_serverless, "serverless")
            r = pd.DataFrame(r)

            msg_to_display = ""
            if not r.empty:
#                 for i in range(len(r["news_key"])):
#                     msg_to_display = msg_to_display + r["body"][i] + "\\n"
                msg_to_display = r.to_json(orient="records", force_ascii=False)
                subject = generate_subject(r, file_key_words, authorized_dict = [])
                sysmg = f"{config.system_message_chat_conversation_withsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}\n\nSources:\n{msg_to_display}"
                append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on (three years ~ current) relavent news start.".format(datetime.today().strftime("%H:%M:%S"))])
                answer = aws.invoke_sonnect(sysmg, final_question)
                if any(i in answer for i in key_word) and flag is False:
                    append_to_log("./consult_log.txt", ["[{}] Claude3 don't know based on (three years ~ current) relavent news.".format(datetime.today().strftime("%H:%M:%S"))])
                    subject = []
                    sysmg = f"{config.system_message_chat_conversation_withoutsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}"
                    append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on what it already known start.".format(datetime.today().strftime("%H:%M:%S"))])
                    answer = aws.invoke_sonnect(sysmg, final_question)
                else:
                     pass
            else:
                append_to_log("./consult_log.txt", ["[{}] No relavent news in (three years ~ current).".format(datetime.today().strftime("%H:%M:%S"))])
                subject = []
                sysmg = f"{config.system_message_chat_conversation_withoutsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}"
                append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on what it already known start.".format(datetime.today().strftime("%H:%M:%S"))])
                answer = aws.invoke_sonnect(sysmg, final_question)
                
        elif any(i in answer for i in key_word) and flag is True:
            append_to_log("./consult_log.txt", ["[{}] Claude3 don't know based on (from ~ to) relavent news.".format(datetime.today().strftime("%H:%M:%S"))])
            subject = []
            sysmg = f"{config.system_message_chat_conversation_withoutsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}"
            append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on what it already known start.".format(datetime.today().strftime("%H:%M:%S"))])
            answer = aws.invoke_sonnect(sysmg, final_question)
        else:
            pass

    elif r.empty and flag is False:
        append_to_log("./consult_log.txt", ["[{}] No relavent news in (half year ~ current).".format(datetime.today().strftime("%H:%M:%S"))])
        config.range_time["range"]["datepublish"]["gte"] = datetime.strftime(datetime.now()-timedelta(days=1095),'%Y-%m-%d')
        config.range_time["range"]["datepublish"]["lte"] = datetime.strftime(datetime.now(),'%Y-%m-%d')
        config.query_body["query"]["bool"]["must"].append(config.range_time) # = [config.range_time]
        # config.query_body["query"]["bool"]["must"][0]["multi_match"]["query"] = search_question
        # config.query_body["query"]["bool"]["should"][0]["multi_match"]["query"] = search_question
        config.query_body["query"]["bool"]["should"][0]["function_score"]["query"]["knn"]["subject_vector"]["vector"] = q_vector
        config.query_body["query"]["bool"]["should"][1]["function_score"]["query"]["knn"]["keyword_vector"]["vector"] = q_vector
        config.query_body["query"]["bool"]["should"][2]["function_score"]["query"]["knn"]["body_vector"]["vector"] = q_vector
        append_to_log("./consult_log.txt", ["[{}] Start search (three years ~ current) time range.".format(datetime.today().strftime("%H:%M:%S"))])
        r = aws.index_search(config.query_body, config.host_serverless, config.index_name_serverless, "serverless")
        r = pd.DataFrame(r)

        msg_to_display = ""
        if not r.empty:
#             for i in range(len(r["news_key"])):
#                 msg_to_display = msg_to_display + r["body"][i] + "\\n"
            msg_to_display = r.to_json(orient="records", force_ascii=False)
            subject = generate_subject(r, file_key_words, authorized_dict = [])
            sysmg = f"{config.system_message_chat_conversation_withsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}\n\nSources:\n{msg_to_display}"
            append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on (three years ~ current) relavent news start.".format(datetime.today().strftime("%H:%M:%S"))])
            answer = aws.invoke_sonnect(sysmg, final_question)
            if any(i in answer for i in key_word) and flag is False:
                append_to_log("./consult_log.txt", ["[{}] Claude3 don't know based on (three years ~ current) relavent news.".format(datetime.today().strftime("%H:%M:%S"))])
                subject = []
                sysmg = f"{config.system_message_chat_conversation_withoutsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}"
                append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on what it already known start.".format(datetime.today().strftime("%H:%M:%S"))])
                answer = aws.invoke_sonnect(sysmg, final_question)
            else:
                 pass
        else:
            append_to_log("./consult_log.txt", ["[{}] No relavent news in (three years ~ current).".format(datetime.today().strftime("%H:%M:%S"))])
            subject = []
            sysmg = f"{config.system_message_chat_conversation_withoutsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}"
            append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on what it already known start.".format(datetime.today().strftime("%H:%M:%S"))])
            answer = aws.invoke_sonnect(sysmg, final_question)
    else:
        append_to_log("./consult_log.txt", ["[{}] No relavent news in (from ~ to).".format(datetime.today().strftime("%H:%M:%S"))])
        subject = []
        sysmg = f"{config.system_message_chat_conversation_withoutsource.format(year=datetime.strftime(datetime.today(),'%Y-%m-%d'))}"
        append_to_log("./consult_log.txt", ["[{}] ask Claude3 to answer based on what it already known start.".format(datetime.today().strftime("%H:%M:%S"))])
        answer = aws.invoke_sonnect(sysmg, final_question)
    del r
    print(f"query body = {config.query_body}")

    image_dict = []
    return {"final_question": final_question, "data_points": msg_to_display, "answer": answer, "subject": subject, "other_subject": [], "image": image_dict, "thoughts": sysmg}

def run_streaming(history: Sequence[dict[str, str]], tk: str, condition: str):
    aws = AWS()
    one_month_ago_first_day, one_month_ago_last_day = get_first_and_last_day_months_ago(months=1)
    three_month_ago_first_day, three_month_ago_last_day = get_first_and_last_day_months_ago(months=3)
    lastweek_first_day, lastweek_last_day = get_first_and_last_day_lastweek_list()
    thisweek_first_day, thisweek_last_day = get_first_and_last_day_thissweek_list()
    sysmg = config.search_query_chat_conversation.format(
        year=datetime.strftime(datetime.today(), "%Y-%m-%d"),
        start=one_month_ago_first_day, end=one_month_ago_last_day,
        start2=three_month_ago_first_day, end2=three_month_ago_last_day,
        start3=lastweek_first_day, end3=lastweek_last_day,
        start4=datetime.strftime(datetime.now()-relativedelta(months=3), "%Y-%m-%d"), end4=datetime.strftime(datetime.today(), "%Y-%m-%d"),
        start5=datetime.strftime(datetime.now()-relativedelta(months=4), "%Y-%m-%d"), end5=datetime.strftime(datetime.today(), "%Y-%m-%d"),
        start6=datetime.strftime(datetime.today()-timedelta(days=14), "%Y-%m-%d"), end6=datetime.strftime(datetime.today(), "%Y-%m-%d"),
        start7=datetime.strftime(datetime.now()-relativedelta(months=12), "%Y"), end7=datetime.strftime(datetime.now()-relativedelta(months=12), "%Y"),
        start8=datetime.strftime(datetime.today(), "%Y-%m-%d"), end8=datetime.strftime(datetime.today(), "%Y-%m-%d"),
        start9=thisweek_first_day, end9=thisweek_last_day,
        start10=datetime.strftime(datetime.today()-timedelta(days=30), "%Y-%m-%d"), end10=datetime.strftime(datetime.today(), "%Y-%m-%d")
    )
    if len(history) >= 1:
        conversation = ""
        for h in history[:-1]:
            conversation += "question: " + h.get("user") + ",\n"
            if h.get("bot"):
                conversation += "answer: " + h.get("bot") + ",\n"
        conversation += "last question: " + history[-1]["user"] + "\n"
        final_question = aws.invoke_sonnect(sysmg, conversation.replace("news", ""))
        del conversation
    else:
        final_question = aws.invoke_sonnect(sysmg, history[-1]["user"].replace("news", ""))

    if "news" in final_question:
        final_question = final_question.replace("news", "").strip()
    elif "NEWS" in final_question:
        final_question = final_question.replace("NEWS", "").strip()

    if "from" in final_question and "to" in final_question:
        from_date = re.search(r"from[:\s]*(\d{4}-\d{2}-\d{2})", final_question)
        to_date = re.search(r"to[:\s]*(\d{4}-\d{2}-\d{2})", final_question)
        set_range_time(from_date.group(1), to_date.group(1))
        # set_range_time(final_question[final_question.find("from"):].split("-", 1)[0][-4:] + "-" + final_question[final_question.find("from"):].split("-", 1)[1][:5], final_question[final_question.find("to"):].split("-", 1)[0][-4:] + "-" + final_question[final_question.find("to"):].split("-", 1)[1][:5])
        search_question = final_question[:final_question.find(f"{from_date.group(0)}")].strip()
        append_to_log(config.consult_log_file, ["[{} - {}] final question = {}".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"), final_question)])
        append_to_log(config.consult_log_file, ["[{} - {}] search question = {}".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"), search_question)])
        q_vector = aws.embedding(search_question, "en")["embedding"]
        # set_query_body(q_vector)
        set_query_body_both(search_question, q_vector)
        # set_query_body_rescore(search_question, q_vector)
        if condition == "ft": # (7)
            append_to_log(config.consult_log_file, ["[{} - {}] filter news in specified (from ~ to) time' relevant news, but don't know answer. (data & unknown)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
            guide = False
            results = []
            subject = []
        else:
            r = aws.index_search(config.query_body_both, config.host_serverless, config.index_name_serverless, "serverless")
            dataframe = filter_dataframe(r)
            if dataframe.empty: # (8)
                append_to_log(config.consult_log_file, ["[{} - {}] no relevant news in specified (from ~ to) time. (!data)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
                guide = False
                results = []
                subject = []
            elif not dataframe.empty: # (9)
                append_to_log(config.consult_log_file, ["[{} - {}] filter news in specified (from ~ to) time' relevant news. (data & !unknown)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
                guide = False
                condition = "ft"
                results = dataframe[["news_key", "datepublish", "subject", "body", "sourcefile", "keyword", "reporter"]].to_json(orient="records", force_ascii=False)
                subject = generate_subject(dataframe, config.file_key_words, authorized_dict=[])
    else:
        search_question = final_question
        q_vector = aws.embedding(search_question, "en")["embedding"]
        append_to_log(config.consult_log_file, ["[{} - {}] final question = {}".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"), final_question)])
        append_to_log(config.consult_log_file, ["[{} - {}] search question = {}".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"), search_question)])
        set_range_time(datetime.strftime(datetime.now()-timedelta(days=180), "%Y-%m-%d"), datetime.strftime(datetime.now(), "%Y-%m-%d"))
        # set_query_body(q_vector)
        set_query_body_both(search_question, q_vector)
        # set_query_body_rescore(search_question, q_vector)
        if condition == "6m" or condition == "5y": # (1) & (4)
            guide = True
        else:
            r = aws.index_search(config.query_body_both, config.host_serverless, config.index_name_serverless, "serverless")
            dataframe = filter_dataframe(r)
            if dataframe.empty: # (2)
                guide = True
            elif not dataframe.empty: # (3)
                append_to_log(config.consult_log_file, ["[{} - {}] filter news in past six months' relevant news. (data & !unknown)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
                guide = False
                condition = "6m"
                results = dataframe[["news_key", "datepublish", "subject", "body", "sourcefile", "keyword", "reporter"]].to_json(orient="records", force_ascii=False)
                subject = generate_subject(dataframe, config.file_key_words, authorized_dict=[])
    if guide is True:
        # config.query_body["query"]["bool"]["must"][0]["range"]["datepublish"]["gte"] = datetime.strftime(datetime.now()-timedelta(days=1825), "%Y-%m-%d")
        config.query_body_both["query"]["bool"]["must"][0]["range"]["datepublish"]["gte"] = datetime.strftime(datetime.now() - timedelta(days=1825), "%Y-%m-%d")
        # config.query_body_rescore["query"]["bool"]["must"][0]["range"]["datepublish"]["gte"] = datetime.strftime(datetime.now()-timedelta(days=1825), "%Y-%m-%d")
        if condition == "5y": # (4)
            append_to_log(config.consult_log_file, ["[{} - {}] filter news in past five years' relevant news, but don't know answer. (data & unknown)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
            results = []
            subject = []
        elif condition == "6m": # (1)
            append_to_log(config.consult_log_file, ["[{} - {}] filter news in past six months' relevant news, but don't know answer. (data & unknown)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
            append_to_log(config.consult_log_file, ["[{} - {}] back to filter news in past five years' relevant news.".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
            r = aws.index_search(config.query_body_both, config.host_serverless, config.index_name_serverless, "serverless")
            dataframe = filter_dataframe(r)
            if dataframe.empty: # (5)
                append_to_log(config.consult_log_file, ["[{} - {}] no relevant news in past five years. (!data % guide)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
                results = []
                subject = []
            elif not dataframe.empty: # (6)
                append_to_log(config.consult_log_file, ["[{} - {}] filter news in past five years' relevant news. (data & !unknown & guide)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
                condition = "5y"
                results = dataframe[["news_key", "datepublish", "subject", "body", "sourcefile", "keyword", "reporter"]].to_json(orient="records", force_ascii=False)
                subject = generate_subject(dataframe, config.file_key_words, authorized_dict=[])
        else: # (2)
            append_to_log(config.consult_log_file, ["[{} - {}] no relevant news in past six months. (!data)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
            append_to_log(config.consult_log_file, ["[{} - {}] back to filter news in past five years' relevant news.".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
            r = aws.index_search(config.query_body_both, config.host_serverless, config.index_name_serverless, "serverless")
            dataframe = filter_dataframe(r)
            if dataframe.empty: # (5)
                append_to_log(config.consult_log_file, ["[{} - {}] no relevant news in past five years. (!data % guide)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
                results = []
                subject = []
            elif not dataframe.empty: # (6)
                append_to_log(config.consult_log_file, ["[{} - {}] filter news in past five years' relevant news. (data & !unknown & guide)".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
                condition = "5y"
                results = dataframe[["news_key", "datepublish", "subject", "body", "sourcefile", "keyword", "reporter"]].to_json(orient="records", force_ascii=False)
                subject = generate_subject(dataframe, config.file_key_words, authorized_dict=[])
    if any(results): # condition = "5y" or condition = "6m" or condition = "ft"
        append_to_log(config.consult_log_file, ["[{} - {}] ask Claude3 to answer based on relavent news start.".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
        sysmg = config.system_message_chat_conversation_withsource.format(year=datetime.strftime(datetime.today(), "%Y-%m-%d")) + "\n\nSources:\n{}".format(results)
    else:
        append_to_log(config.consult_log_file, ["[{} - {}] ask Claude3 to answer based on what it have already known start.".format(datetime.today().strftime("%Y/%m/%d"), datetime.today().strftime("%H:%M:%S"))])
        sysmg = config.system_message_chat_conversation_withoutsource.format(year=datetime.strftime(datetime.today(), "%Y-%m-%d"))
        condition = "end"
        # sysmg = []
        # other_subject = []
        # image_dict = []
        # return results, sysmg, subject, other_subject, image_dict, flag, final_question
    other_subject = []
    image_dict = []
    subject = pd.DataFrame(subject)
    subject = subject.drop_duplicates(subset=["title"]).reset_index(drop=True)
    subject = subject.to_dict("records")
    return results, sysmg, subject, other_subject, image_dict, condition, final_question