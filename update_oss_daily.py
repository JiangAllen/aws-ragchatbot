from preprocessing import update_news_serverless, update_news_provisioned
import schedule
import time
schedule.every().day.at("10:40").do(update_news_serverless) # update_news_provisioned
schedule.every().day.at("13:40").do(update_news_serverless) # update_news_provisioned
schedule.every().day.at("16:40").do(update_news_serverless) # update_news_provisioned
schedule.every().day.at("19:40").do(update_news_serverless) # update_news_provisioned
while True:
    schedule.run_pending()
    time.sleep(10)