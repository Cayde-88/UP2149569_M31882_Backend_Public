import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from secret.secret import em_pw

class EmailClient_cancel:

    def __init__(self, receiver_email, sender_email='ezlimrongyi@gmail.com', password=em_pw):
        self.sender_email = sender_email
        self.receiver_email = receiver_email
        self.password = password

        message = MIMEMultipart("alternative")
        message["Subject"] = "[Tradebotix Notice] Your subscription has ended."
        message["From"] = sender_email
        message["To"] = receiver_email

        # Create the plain-text and HTML version of your message
        text = """\
        """
        html = """\
            <html>
            <head>
                <style>
                    /* Center the content horizontally and vertically */
                    body {
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        text-align: center;
                    }
                    /* Add some styling to the main text */
                    p.main-text {
                        font-size: 18px;
                    }
                    /* Style the disclaimer with a smaller font size */
                    p.disclaimer {
                        font-size: 14px;
                        color: #777; /* You can adjust the color as needed */
                    }
                    /* Center the image and text horizontally */
                    .content {
                        text-align: center;
                    }
                </style>
            </head>
            <body>
                <div class="content">
                    <!-- Set the width and height to make the image smaller -->
                    <img src="https://drive.google.com/uc?export=view&id=1hK32BN0cxPPB91NBTNCW8nW4nD5UwKl7" alt="Thank you" height="250">
                    <p class="main-text">Hi there!<br><br>
                    Thanks again for using the Tradebotix application.<br>
                    Just to let you know, your subscription has ended.<br>
                    If you wish to continue using the application, please visit the page <a href="https://tradebotix.streamlit.app/">here</a> to resubmit your request for the bot to run.<br><br>
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

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)

        # Create secure connection with server and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, receiver_email, message.as_string()
            )

