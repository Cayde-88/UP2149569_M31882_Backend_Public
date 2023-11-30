import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from secret.secret import em_pw
import alpaca_trade_api as tradeapi
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import mpld3

path = os.getcwd()
os.chdir(path)

class EmailClient_portfolio:

    def __init__(self, receiver_email, api_key, secret_key, sender_email='ezlimrongyi@gmail.com', password=em_pw):
        self.sender_email = sender_email
        self.receiver_email = receiver_email
        self.password = password
        self.api_key = api_key
        self.secret_key = secret_key

        message = MIMEMultipart("alternative")
        message["Subject"] = "[Tradebotix Notice] Your Weekly Portfolio Update"
        message["From"] = sender_email
        message["To"] = receiver_email

        # To generate the portfolio summary table
        api = tradeapi.REST(api_key, secret_key, base_url='https://paper-api.alpaca.markets', api_version='v2')
        history = api.get_portfolio_history()
        equity = history.equity
        profit_loss = history.profit_loss
        profit_loss_pct = history.profit_loss_pct

        data = {'Equity (USD)': equity, 'Profit/Loss': profit_loss, 'Profit/Loss (%)': profit_loss_pct}

        df_equity = pd.DataFrame(data, index=history.timestamp)
        dates = [datetime.datetime.fromtimestamp(ts) for ts in df_equity.index.astype(int)]
        df_equity.index = dates

        # sort by date
        df_equity = df_equity.sort_index(ascending=False)

        # plot the equity & export to html
        plt.figure(figsize=(12,10))
        plt.plot(df_equity.index, df_equity['Equity (USD)'], linewidth=2, color='blue')
        plt.xlabel('Date')
        plt.xticks(rotation=45)
        plt.ylabel('Equity (USD)')
        plt.title('Your Portfolio Equity')
        plt.savefig('equity.png')

        pic_html = mpld3.fig_to_html(plt.figure())

        # Dataframe for gainers and losers
        position_data = []

        if api.list_positions() == []: # if no positions
            top_gainers_html = "No positions in portfolio."
            top_losers_html = "No positions in portfolio."
            pass

        else:
            for position in api.list_positions():
                symbol = position.symbol
                unrealized_pl = position.unrealized_pl
                unrealized_plpc = position.unrealized_plpc
                market_val = position.market_value
                cost_basis = position.cost_basis

                position_data.append({
                    'Symbol': symbol,
                    'Unrealized P/L': unrealized_pl,
                    'Unrealized P/L %': unrealized_plpc,
                    'Market Value': market_val,
                    'Cost Basis': cost_basis
                })

            position_df = pd.DataFrame(position_data)

            # Convert to float
            position_df["Unrealized P/L"] = position_df["Unrealized P/L"].astype(float)
            position_df["Unrealized P/L %"] = position_df["Unrealized P/L %"].astype(float)

            # Round to 2 decimals
            position_df["Unrealized P/L"] = np.round(position_df["Unrealized P/L"], 2)
            position_df["Unrealized P/L %"] = np.round(position_df["Unrealized P/L %"], 2)

            # Top 3 gainers
            top_gainers = position_df[position_df['Unrealized P/L'] > 0]

            if len(top_gainers) == 0:
                top_gainers_html = "No gainers in portfolio."

            else:
                top_gainers = top_gainers.sort_values(by=['Unrealized P/L'], ascending=False).head(3)
                top_gainers.reset_index(inplace=True)
                top_gainers.drop(columns=['index'], inplace=True)
                top_gainers.index += 1
                top_gainers_html = top_gainers.to_html()

            # Top 3 losers
            top_losers = position_df[position_df['Unrealized P/L'] < 0]
            if len(top_losers) == 0:
                top_losers_html = "No losses in portfolio."

            else:
                top_losers = top_losers.sort_values(by=['Unrealized P/L'], ascending=True).head(3)
                top_losers.reset_index(inplace=True)    
                top_losers.drop(columns=['index'], inplace=True)
                top_losers.index += 1
                top_losers_html = top_losers.to_html()

        # Create the plain-text and HTML version of your message
        text = """\
        """
        html = f"""\
            <html>
            <head>
                <style>
                    /* Center the content horizontally and vertically */
                    body {{
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 70vh;
                        text-align: center;
                    }}
                    /* Add some styling to the main text */
                    p.main-text {{
                        font-size: 18px;
                    }}
                    /* Style the disclaimer with a smaller font size */
                    p.disclaimer {{
                        font-size: 14px;
                        color: #777; /* You can adjust the color as needed */
                    }}
                    /* Center the image and text horizontally */
                    .content {{
                        text-align: center;
                    }}
                    /* Resize the image to match the width of the text */
                    .image img {{
                        max-width: 100%;
                        height: auto;
                    }}
                </style>
            </head>
            <body>
                <div class="content">
                    <!-- Set the width and height to make the image smaller -->
                    <img src="https://drive.google.com/uc?export=view&id=1R13AjGl78juiDHuPITYB4-x2Ib-6tfRV" alt="Summary" height="250">
                    <p class="main-text">Your Weekly Portfolio Summary is here.<br><br>
                    Thanks again for using the Tradebotix application.<br>
                    This is a weekly update on your portfolio. <br>

                    <h3>Portfolio Summary</h3>
                    <div class = "image">
                        <img src="cid:equity" alt="Equity" width="800">
                    </div>

                    <h3>Top 3 Gainers</h3>
                    <table style="margin: 0 auto; text-align: center;">
                        {top_gainers_html}
                    </table>

                    <h3>Top 3 Losers</h3>
                    <table style="margin: 0 auto; text-align: center;">
                        {top_losers_html}
                    </table><br><br>

                    If you wish to stop receiving this email but continue trading, please visit the page <a href="https://tradebotix.streamlit.app/">here</a> to resubmit your request w/o an email account.<br><br>
                    Thanks and have a great day!<br><br>

                    Best Wishes, <br>
                    Rong Yi
                    </p>
                    <!-- Disclaimer with smaller font size -->
                    <p class="disclaimer">Disclaimer: You are receiving this email because you have provided your email address. <br> If this email was sent to you by mistake, please contact me <a href="mailto:ezlimrongyi@gmail.com">here</a>. </p>
                </div>
            </body>
            </html>
        """

        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        # Attach the Matplotlib chart image as an inline image with Content-ID
        img = open('equity.png', 'rb').read()
        msgImg = MIMEImage(img, 'png')
        msgImg.add_header('Content-ID', '<equity>')
        msgImg.add_header('Content-Disposition', 'inline', filename='equity.png')

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)
        message.attach(msgImg)

        # Create secure connection with server and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, receiver_email, message.as_string()
            )