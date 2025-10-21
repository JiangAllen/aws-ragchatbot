import logging
import pprint
import random
import datetime
current_time = datetime.datetime.now()

aws_access_key_id = ""
aws_secret_access_key = ""

pp = pprint.PrettyPrinter(indent=2)
suffix = random.randrange(200, 900)
logging.basicConfig(filename="./oss.log", level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
consult_log_file = ""
upload_path = ""
arn = ""
field_menu = {
    "settings": {
        "index.knn": True,
        "index": {
            "analysis": {
                "analyzer": {
                    "synonym_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["synonym_filter"]
                    }
                },
                "filter": {
                    "synonym_filter": {
                        "type": "synonym",
                        "synonyms_path": "analyzers/F59142732",
                        "updateable": True
                    }
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "subject": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "synonym_analyzer"
            },
            "subject_vector": {
                "type": "knn_vector",
                "dimension": 1024,
            },
            "datepublish": {
                "type": "date",
            },
            "news_key": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "synonym_analyzer"
            },
            "keyword": {
                "type": "text", # keyword
                "analyzer": "standard",
                "search_analyzer": "synonym_analyzer"
            },
            "keyword_vector": {
                "type": "knn_vector",
                "dimension": 1024,
            },
            "body": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "synonym_analyzer"
            },
            "body_vector": {
                "type": "knn_vector",
                "dimension": 1024,
            },
            "reporter": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "synonym_analyzer"
            },
            "reporter_vector": {
                "type": "knn_vector",
                "dimension": 1024,
            },
            "sourcefile": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "synonym_analyzer"
            },
            "sourcetype": {
                "type": "text", # keyword
                "analyzer": "standard",
                "search_analyzer": "synonym_analyzer"
            },
            "sourcetype_vector": {
                "type": "knn_vector",
                "dimension": 1024,
            }
        }
    }
}
custom_field = []
host_serverless = ""
index_name_serverless = ""
host_provisioned = ""
index_name_provisioned = ""
query_time_decay = {
    "size": 3,
    "_source": [],
    "query": {
        "bool": {
            "should": [
                {
                    "function_score": {
                        "exp": {
                            "datepublish": {
                                "origin": current_time.isoformat(),
                                "scale": "1d",
                                "offset": "0d",
                                "decay": 0.5
                            }
                        },
                    },
                },
            ]
        }
    },
}
range_time = {
    "range": {
        "datepublish": {
            "gte": "",
            "lte": "",
        },
    }
}
query_body = {
    # "explain": True,
    # "profile": True,
    "size": 20,
    "_source": [],
    "query": {
        "bool": {
            "must": [],
            "should": [
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "subject_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.8,
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "keyword_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.6,
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "body_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.4,
                    },
                },
            ],
            "filter": []
        }
    },
}
query_body_both = {
    # "explain": True,
    # "profile": True,
    "size": 20,
    "_source": [],
    "query": {
        "bool": {
            "must": [],
            "should": [
                {
                    "function_score": {
                        "query": {
                            "match": {
                                "subject": {
                                    "query": ""
                                }
                            }
                        },
                        "weight": 0.8
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "subject_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.8,
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "keyword_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.6,
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "body_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.4,
                    },
                },
            ],
            "filter": []
        }
    },
}
query_body_rescore = {
    # "explain": True,
    # "profile": True,
    "size": 20,
    "_source": [],
    "query": {
        "bool": {
            "must": [],
            "should": [
                {
                    "bool": {
                        "must": [
                            {
                                "function_score": {
                                    "query": {
                                        "match": {
                                            "subject": {
                                                "query": ""
                                            }
                                        }
                                    },
                                    "weight": 0.8
                                }
                            }
                        ]
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "subject_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.8,
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "keyword_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.6,
                    }
                },
                {
                    "function_score": {
                        "query": {
                            "knn": {
                                "body_vector": {
                                    "vector": "",
                                    "k": 1024
                                },
                            },
                        },
                        "weight": 0.4,
                    },
                },
            ],
            "filter": []
        }
    },
    "rescore": {
        "window_size": 10,
        "query": {
            "rescore_query": {
                "match": {
                    "subject": {
                        "query": ""
                    }
                }
            },
            "query_weight": 1.0,
            "rescore_query_weight": 0.5
        }
    }
}
query_file_id = {
    "size": 30,
    "_source": [],
    "query": {
        "match": {
            "news_key": ""
        }
    }
}
model_eb = ""
model_sn = ""
model_hk = ""
search_query_chat_conversation = "You are an AI assistant, helping people generate a search query. Always obey the following rules: (1.) Must generate a clear and unambiguous search query based on the history of the conversation and the last question. The Last question is the most important. The Last question MUST be the first priority you consider. (2.) MUST Only return the search query you generate, MUST Don't return any other text in your answer. (3.) MUST DON'T return any web site in the search query. (4.) MUST don't use any symbol to connect the seach query. (5.) Must answer in english. (6.) Current date is {year}, ONLY If there are date and time expressions in the Search Query, you calculate based on today and convert all of them into the format as 'from: yyy-mm-dd, to: yyyy-mm-dd'. 'last month' is the month that was one month before the current month, it should be converted into a time interval from the first date of the month which is one month ago to the last date of the month which is one month ago; '3 months ago' is the month that was three months before the current month, it should be converted into a time interval from the first date of the month which is 3 months ago to the last date of the month which is 3 month ago; 'last week' is the corresponding week that was 7 days before the current date, it should be converted into the time interval from the fist date of coresponding week to the last date of coresponding week; 'past 3 months' should be converted into the time interval which is from 3 months ago to current date; 'past 4 months' should be converted into the time interval which is from 4 months ago to current date; 'past two weeks' should be converted into the time interval which is from 14 days ago to current date; 'last year' should be converted into the time interval of last year, which means from the first date of previous year to the last date of previous year; '2023/3' should be converted into the time interval of March 2023, which means from the first date of March to the last date of March; 'October 2023' should be converted into the time interval of March 2023, which means from the first date of March to the last date of March; 'last September' should be converted into the time interval of September in the last year, which means from the first date of last September to the last date of last September. (5.) MUST DON'T return any web site in the search query. (6.) If there are no time expressions in the conversation and the last question, MUST don't generate time in the search query. (7.) Check and revise repeatly the search query you generate before you return the answer.(8.) MUST don't use any symbol to connect the seach you create. Examples:Today is {year}. H: how about the revenue of TSMC last month A: how about the revenue of TSMC from: {start}, to: {end} H: news 3 months ago A: news 3 months ago from: {start2}, to: {end2} H: Contents of COMPUTEX held last week A: Contents of COMPUTEX held from: {start3}, to: {end3} H: news from the past 3 months A: news from: {start4}, to: {end4} H: news from the past 4 months A: news from: {start5}, to: {end5} H: daily temperatures from the past two weeks A: daily temperatures from {start6}, to: {end6} H: how many disasters we encountered last september A:  how many disasters we encountered from {start7}-09-01, to: {end7}-09-30 H: news on 2010/08/09 A: news from 2010-08-09, to: 2010-08-09 H: today's informations about Intel A: informations about Intel from {start8}, to: {end8} H: Contents of WWDC held this week A: Contents of WWDC held from: {start9}, to: {end9}. H: recent tsmc A: tsmc from: {start10}, to: {end10}."
system_message_chat_conversation_withsource = """Now is A.D. {year}, You are an AI assistant, you should ONLY answer according to the relevant data listed in the list of sources below. All the source are json format with keys e.g. news_key, datepublish, subject, keyword, reporter, sourcetype, body. MUST always obey th following rules when you answer. (1.) In the source, the key named datepublish is published date of data itself. Just answer according to the published date if you need but MUST Don't return it in your answer. (2.) In the source, the key named reporter is the writer of data, you MUST refer to it when you are asked to answer according to the specific writer. (3.) In the source, the key named sourcetype is the type of data, you MUST refer to it when you are asked to answer according to the specific type of data. (4.) In the source, the key named body is the main contents of data. You MUST ONLY refer to the highly relevant contents, if there are no highly relevant contents in the list of sources below, then just answer you don't know. (5.) In the source, the key named keyword are some key words of the corresponding data. You should refer to them to judge whether the corresponding data is relevant to the question.(6.) Answer in english. (7.) Must not return unit in any kind of bracket. (8.) MUST not return html format. Do not return markdown format. (9.) Answer in detail. Furthermore, While you are asked to analyze with SWOT, additionally obeying the following rules. (1.) answering ONLY according to the data listed in the list of sources below. (2.) strengths are internal factors that give an organization an advantage over others. These could include full of diversity, innovation, good quality of products or services, higher value of products or services, advanced skills, unique skills, unique services, capabilities, market reputation, good business management. (3.) Weaknesses are internal factors that may place an organization at a disadvantage compared to others. These could include lack of diversity, areas needing improvement, lack of resources, or internal conflicts, bad quality of products or services, lower value of products or services, outdated skills, bad business management. (4.) Opportunities are external factors in the environment that the organization could exploit to its advantage. These could include higher market entry barriers, decreasing price of raw materials, market trends, increase in demand, lower market competition, economic prosperity, positive government policies, or changes in regulations. (5.) Threats are external factors in the environment that could potentially cause trouble for the organization. These could include lower market entry barriers, increasing price of raw materials, wars, natural disasters, decrease in demand, higher market competition, economic downturns, changes in consumer preferences, negative government policies, or legal issues. (6.) MUST DONT regard external factors in the environment as internal strengths. (7.) MUST DONT regard external factors in the environment as internal Weaknesses. (8.) MUST DONT regard internal strengths as external Opportunities. (9.) MUST DONT regard internal Weaknesses as external Threats. (10.) In the beginning of each data, published date of data itself are included in parentheses. MUST notice the timing of data listed below, You can only refer to data that is consistent with the time frame mentioned in the question. While you are asked to analyze with Porter five forces analysis, additionally obeying the following rules. (1.) answering ONLY according to the data listed in the list of sources below. (2.) Threat of New Entrants means how easy or difficult for new competitors to enter the industry. Barriers to entry can influence this threat e.g., economies of scale, brand loyalty, capital requirements and government regulations. (3.) Bargaining Power of Suppliers means suppliers' ability to raise prices or reduce the quality of goods and services they provide. This force is high when few suppliers dominate the market or when there are few substitutes for the supplier's product. (4.) Bargaining Power of Buyers means customers' power to negotiate prices and terms. It is high when buyers have many choices, low switching costs, and significant purchasing volume. (5.) Threat of Substitute Products or Services means the availability of alternative products or services that could satisfy the same customer needs. The higher the availability of substitutes, the more intense the competition. (6.) Intensity of Competitive Rivalry examines the level of competition among existing firms in the industry. Factors such as industry growth rate, number of competitors, and differentiation among products or services contribute to the intensity of rivalry. (7.) MUT don't combine Porter five forces analysis with SWOT. (8.) In the beginning of each data, published date of data itself are included in parentheses. MUST notice the timing of data listed below, You can only refer to data that is consistent with the time frame mentioned in the question."""
system_message_chat_conversation_withoutsource = """Now is {year}, You are an AI assistant. The assistant is helpful, creative, clever, and very friendly. Answer in english. Answer with the facts you already known, if you do not know the answer, then say you do not know."""
key_word = ["Unfortunately", "unfortunately", "sorry", "don't know", "do not know", "don't understand", "do not understand"]
file_key_words = []
max_tokens_to_sample = 4096
temperature = 0.5
topK = 250
topP = 0.5
filter_socre = 5.0