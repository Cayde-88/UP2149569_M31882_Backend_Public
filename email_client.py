# for performing SQL queries
import sqlalchemy as db
import pandas as pd
import datetime
from secret.secret import host, database, user, password
from email_template_cancel import EmailClient_cancel
from email_template_portfolio import EmailClient_portfolio

engine = db.create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')

def send_email():

    if engine.execute("""SELECT * FROM users""").fetchall() == []:
        print("No users in database, no emails sent.")
        pass

    else:
        # Query the users' email with 'Cancel' status
        cancel_result = engine.execute("""SELECT email FROM users WHERE days_to_trade = 'Cancel'""").fetchall()
        users_table = pd.DataFrame(cancel_result, columns = ["email"])

        # send email to users
        for email in users_table["email"]:
            if email == None:
                pass
            else:                      
                email_client = EmailClient_cancel(receiver_email=email)
        
        print("Emails sent to users with 'Cancel' status.")

        # Query the users' email with non-'Cancel' status (to send portfolio summary table)
        portfolio_result = engine.execute("""SELECT email, api_key, secret_key, date_submitted from users WHERE days_to_trade != 'Cancel'""").fetchall()
        users_table = pd.DataFrame(portfolio_result, columns = ["email", "api_key", "secret_key", "date_submitted"]) 

        # Calculate the days difference between today and the date the user submitted the request
        today = datetime.datetime.today()
        users_table["date_submitted"] = pd.to_datetime(users_table["date_submitted"])
        users_table["days_difference"] = (today - users_table["date_submitted"]).dt.days

        # Only keep users with days_difference % 7 == 0 (to ensure that it is a week since the user submitted the request)
        # Users will receive an email on day 0, as a reminder that they have submitted a request
        users_table = users_table[users_table["days_difference"] % 7 == 0]

        if len(users_table) == 0:
            print("No users with non-'Cancel' status, no emails sent.")
            pass

        else:
            for _, row in users_table.iterrows():
                email = row["email"]
                api_key = row["api_key"]
                secret_key = row["secret_key"]

                if email == None:
                    pass
                else:                      
                    email_client = EmailClient_portfolio(receiver_email=email, api_key=api_key, secret_key=secret_key)
            
            print("Emails sent to users with their weekly portfolio summary table.")

        
        

