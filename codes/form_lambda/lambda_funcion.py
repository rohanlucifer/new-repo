import json
import cgi
import io
from cgi import FieldStorage
import base64
import requests
import pandas as pd
import boto3
import email, smtplib, ssl
import os

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



def lambda_handler(event, context):
    env = os.environ['branch']

    email_user_id = os.environ['email_user_id']
    email_password = os.environ['email_password']
    email_port = 587
    email_server = os.environ['email_server']

    # handle incoming fields
    # remove extra whitespace
    # split into usable dictionary
    print(event)
    print(event['body'])
    base64_bytes = event['body'].encode('utf8')
    message_bytes = base64.b64decode(base64_bytes)
    form_data = message_bytes.decode('utf8')
    headers = event['headers']
    content_type = headers['content-type']
    ctype, pdict = cgi.parse_header(content_type)
    boundry = '--' + pdict['boundary']
    form_data = form_data.replace('\r', '\n')
    form_data = form_data.replace('\n\n\n\n', '\n')
    form_data = form_data.replace('\n\n', '\n')
    form_data = form_data.split(boundry)
    print(form_data)
    fields = {}
    for idx, data in enumerate(form_data):
        if '"' in data:
            ignore = ['storeShelfPhoto', 'storeTillPhoto', 'storeCashierPhoto']
            fieldname = data.split('"')[1]
            value = data.split('"')[2].strip()
            fields[fieldname] = value

    # Make sure all fields required for store master file are present. If not add as NA.
    reqFields = ['Country', 'ownerName', 'ownerMobile', 'retailerName', 'retailerAddress', 'storeName', 'storeAddress'
        , 'storeB2BSales', 'storeShelfSpace', 'storeOnlineSales', 'storeSurrounding', 'storeSecondaryType', 'storeSize',
                 'storeLatitude', 'storeLongitude', 'storeRegion', 'storeProvince', 'storeCity', 'storeChannel',
                 'Agency', 'ownerBankName', 'ownerBankAccountName', 'ownerBankAccountNumber', 'storeBanner']

    for reqField in reqFields:
        if reqField in fields:
            if not fields[reqField]:
                fields[reqField] = 'NA'
        else:
            fields[reqField] = 'NA'

    # Add EN fields if missing from the request. I.e for Indonesisa the EN fields are hidden as they have the same input for EN and Local.
    ENFields = ['retailerNameEN', 'retailerAddressEN', 'storeNameEN', 'storeAddressEN']
    for ENField in ENFields:
        size = len(ENField)
        regField = ENField[:size - 2]
        if ENField in fields:
            if not fields[ENField]:
                if regField in fields:
                    fields[ENField] = fields[regField]
                else:
                    fields[ENField] = 'NA'
        else:
            if regField in fields:
                fields[ENField] = fields[regField]
            else:
                fields[ENField] = 'NA'

    dialingCode = ''

    # set variables for excel file, these are fixed per panel / country so we don't ask users to fill them in and set them here.
    if fields['Country'] == 'TH':
        panel_name = 'eyos connect Thailand'
        countryCode = fields['Country']
        fields['Country'] = 'Thailand'
        template_id = os.environ['contract_template_id_TH']
        city = fields['storeProvince']
    elif fields['Country'] == 'ID':
        panel_name = 'eyos connect Indonesia'
        countryCode = fields['Country']
        fields['Country'] = 'Indonesia'
        template_id = os.environ['contract_template_id_ID']
        city = fields['retailerCity']
    else:
        panel_name = 'NA'
        countryCode = 'NA'
        dialingCode = ''

    # open s3 client
    s3 = boto3.resource('s3')

    # Available store codes are stored in S3 (saves on a DB connection). Store codes are generated in Bulk in advance using the Store Onboarding Process.
    # Get Fresh store code
    code = s3.meta.client.list_objects_v2(
        Bucket=os.environ['store_code_bucket'],
        MaxKeys=2,
        Prefix=os.environ['store_code_path'] + '/' + countryCode + '/'
    )
    print(code['Contents'])
    code = code['Contents'][1]['Key']
    code = code.split('/')[-1]
    blank_store_code = code

    # setting photos
    if countryCode != 'NA':
        photoFields = ['storeFrontPhotos3', 'storeShelfPhotos3', 'storeTillPhotos3']
        for photo in photoFields:
            if fields[photo]:
                sourceKey = fields[photo].split('https://ap-southeast-1.amazonaws.com/install.emporio.ai/')[1]
                print(sourceKey)
                sourceFileExt = fields[photo].split('.')[-1]
                print(sourceFileExt)
                copy_source = {
                    'Bucket': 'install.emporio.ai',
                    'Key': sourceKey
                }
                if 'Shelf' in photo:
                    ident = 'SHELF'
                elif 'Till' in photo:
                    ident = 'TILL'
                else:
                    ident = 'STORE'
                destKey = countryCode + '/' + ident + '/' + blank_store_code + '.' + sourceFileExt
                print(destKey)
                try:
                    s3.meta.client.copy(copy_source, 'eyos-store-profile', destKey)
                    fields[photo] = 's3://eyos-store-profile' + destKey
                except Exception as e:
                    fields[photo] = 'NA'
                    print('Failed Uploading Photo To eyos-store-profile')
                    print('Source Photo was: ' + sourceKey)
                    print('Source File Ext was:' + sourceFileExt)
                    print(str(e))


            else:
                fields[photo] = 'NA'
    else:
        fields['storeFrontPhotos3'] = 'NA'
        fields['storeShelfPhotos3'] = 'NA'
        fields['storeTillPhotos3'] = 'NA'

    storePhoto = 'NA'
    tillPhoto = 'NA'
    shelfPhoto = 'NA'

    # fixing % variables
    percFix = ['storeB2BSales', 'storeOnlineSales', 'storeShelfSpace']
    for data in percFix:
        if fields[data] != 'NA':
            fields[data] = float(fields[data]) / 100

    # store online sales yes/no fix
    if fields['storeOnlineSales'] != 'NA':
        storeOnlineYN = 'YES'
    else:
        storeOnlineYN = 'NA'

    # strip plus sign for store master
    if (fields['ownerMobile'][0] == '+'):
        smMobile = fields['ownerMobile'][1:]
    else:
        smMobile = fields['ownerMobile']

    # build excel file format
    excel = {}
    excel['COUNTRY_NAME'] = fields['Country']
    excel['RETAILER CODE / LE CODE'] = 'NA'
    excel['STORE CODE'] = blank_store_code
    excel['PANEL NAME'] = panel_name
    excel['RETAILER OWNER NAME'] = fields['ownerName']
    excel['RETAILER OWNER MOBILE NO'] = smMobile
    excel['RETAILER NAME'] = fields['retailerName']
    excel['RETAILER NAME (EN)'] = fields['retailerNameEN']
    excel['RETAILER ADDRESS'] = fields['retailerAddress']
    excel['RETAILER ADDRESS (EN)'] = fields['retailerAddressEN']
    excel['STORE USER NAME'] = 'NA'
    excel['STORE USER MOBILE NO'] = 'NA'
    excel['STORE NAME'] = fields['storeName']
    excel['STORE NAME (EN)'] = fields['storeNameEN']
    excel['STORE ADDRESS'] = fields['storeAddress']
    excel['STORE ADDRESS (EN)'] = fields['storeAddressEN']
    excel['STORE LATITUDE'] = fields['storeLatitude']
    excel['STORE LONGITUDE'] = fields['storeLongitude']
    excel['STORE REGION'] = fields['storeRegion']
    excel['STORE SUBREGION'] = fields['storeProvince']
    excel['STORE PROVINCE'] = fields['storeProvince']
    excel['STORE CITY'] = fields['storeCity']
    excel['STORE CHANNEL NAME / STORE TYPE'] = fields['storeChannel']
    excel['STORE CHANNEL SEGMENT'] = 'NA'
    excel['STORE EXTERNAL PROGRAM'] = 'NA'
    excel['STORE TILL COUNT'] = 'NA'
    excel['STORE POS'] = 'NA'
    excel['DISTRIBUTOR CODE'] = 'NA'
    excel['DISTRIBUTOR NAME'] = 'NA'
    excel['DISTRIBUTOR TYPE'] = 'NA'
    excel['FIELD TEAM - ONBOARD'] = fields['Agency']
    excel['FIELD TEAM - MANAGE'] = 'NA'
    excel['STORE CONNECTIVITY'] = 'NA'
    excel['STORE DEVICE BRAND MODEL'] = 'NA'
    excel['STORE DEVICE SERIAL NUMBER'] = 'NA'
    excel['STORE PAYMENT TYPE'] = 'NA'
    excel['STORE BANK NAME'] = 'NA'
    excel['STORE BANK CODE'] = fields['ownerBankName']
    excel['STORE ACCOUNT NAME'] = fields['ownerBankAccountName']
    excel['STORE ACCOUNT NUMBER'] = fields['ownerBankAccountNumber']
    excel['STORE USER DISBURSEMENT FLAG'] = 'NA'
    excel['STORE POS AVAILABILITY'] = 'NA'
    excel['STORE POS SERIAL NUMBER'] = 'NA'
    excel['STORE ACTION STATUS'] = 'NA'
    excel['STORE ACTION DETAIL'] = 'NA'
    excel['STORE ACTION DATE'] = 'NA'
    excel['STORE CAMPAIGN READINESS'] = 'NA'
    excel['STORE CONTRACT SIGNOFF'] = 'NA'
    excel['STORE CONTRACT SIGNED BY'] = 'NA'
    excel['STORE TNC ACCEPTED FLAG'] = 'NA'
    excel['STORE TNC ACCEPTED DATETIME'] = 'NA'
    excel['STORE TNC TYPE'] = 'NA'
    excel['STORE SIZE'] = fields['storeSize']
    excel['STORE SHELF SPACE'] = fields['storeShelfSpace']
    excel['STORE ONLINE SALES'] = storeOnlineYN
    excel['STORE B2B SALES PERCENTAGE'] = fields['storeB2BSales']
    excel['STORE FRONT PHOTO'] = fields['storeFrontPhotos3']
    excel['STORE TILL PHOTO'] = fields['storeTillPhotos3']
    excel['STORE SHELF PHOTO'] = fields['storeShelfPhotos3']
    excel['STORE SURROUNDING TYPE'] = fields['storeSurrounding']
    excel['STORE SECONDARY TYPE'] = fields['storeSecondaryType']
    excel['STORE ONLINE SALES PERCENTAGE TILL'] = fields['storeOnlineSales']
    excel['STORE BANNER'] = fields['storeBanner']

    print(fields)
    df = pd.DataFrame(excel, index=[0])
    df.to_excel('/tmp/file.xlsx', sheet_name='Data', index=False)

    # push store master
    destBucket = os.environ['store_master_bucket']
    destKey = 'eyos-connect/' + countryCode + '/STORE_MASTER/inbox/Onboarding Form Store Master - ' + blank_store_code + '.xlsx'

    # backup store-master upload
    backupBucket = 'install.emporio.ai'
    backupKey = 'BACKUP/' + countryCode + '/STORE_MASTER/inbox/Store Master - ' + blank_store_code + '.xlsx'

    if countryCode != 'NA':
        print("uploading store master file")
        try:
            s3.meta.client.upload_file('/tmp/file.xlsx', destBucket, destKey)
            s3.meta.client.upload_file('/tmp/file.xlsx', backupBucket, backupKey)
        except Exception as e:
            print(e)

    # Delete Store ID File (if Production) to ensure the store code isn't used again.
    if env == 'production':
        s3.Object('install.emporio.ai', 'STORE_CODE/' + countryCode + '/' + blank_store_code).delete()

    # create contract
    # contractFields = ['retailerName','retailerCompanyID','ownerName','ownerMobile','ownerPhone','retailerAddress','retailerPostCode','retailerCity','ownerEmail']
    # for

    company_name = fields['retailerName']
    company_number = fields['retailerCompanyID']
    owner_name = fields['ownerName']
    owner_mobile = fields['ownerMobile']
    owner_phone = fields['ownerPhone']
    address = fields['retailerAddress']
    post_code = fields['retailerPostCode']
    # city is defined above.

    owner_email = fields['ownerEmail']

    if owner_email != '':
        contact_method = 'email'
        contact_value = owner_email
    else:
        contact_method = 'mobile'
        contact_value = owner_mobile

    #if not in production, use test mode for a free contract.
    contractTest = "no"
    if env != 'production':
        contractTest = "yes"

    json_body = {"template_id": template_id,
                 "test": contractTest,
                 "signers": [
                     {
                         "name": owner_name,
                         contact_method: contact_value
                     }
                 ],
                 "placeholder_fields": [
                     {
                         "api_key": "company_number",
                         "value": company_number
                     },
                     {
                         "api_key": "company_name",
                         "value": company_name
                     },
                     {
                         "api_key": "address",
                         "value": address
                     },
                     {
                         "api_key": "post_code",
                         "value": post_code
                     },
                     {
                         "api_key": "city",
                         "value": city
                     },
                     {
                         "api_key": "owner_name",
                         "value": owner_name
                     },
                     {
                         "api_key": "owner_phone",
                         "value": owner_phone
                     },
                     {
                         "api_key": "owner_mobile",
                         "value": owner_mobile
                     },
                     {
                         "api_key": "owner_email",
                         "value": owner_email
                     },
                     {
                         "api_key": "store_code",
                         "value": blank_store_code
                     }
                 ]
                 }

    responseTC = requests.post('https://5fb034ee-6484-4728-9f43-0312971dc400:@esignatures.io/api/contracts',
                                   json=json_body)
    contractURL = responseTC.json()['data']['contract']['signers'][0]['sign_page_url']

    response = {
        "statusCode": 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps({
            'storeCode': blank_store_code,
            'storeName': fields['storeName'],
            'contractURL': contractURL
        })
    }

    def post_slack_comment(data, store_code):
        comment = ''
        for key in data:
            comment = comment + '*' + key + '*: ' + str(data[key]) + '\n'
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "New Store Onboarded | " + store_code
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": comment
                    }
                ]
            }
        ]
        headers = {
            'Authorization': 'Bearer xoxb-3932992108-2248384616707-jEzDbaMuoAMYPAeVmPnTUjLg',
        }
        payload = {'blocks': json.dumps(blocks),
                   'channel': 'C02C5RZKWP6'
                   }

        response = requests.post('https://slack.com/api/chat.postMessage', headers=headers, data=payload)

    def send_email(data, store_code):
        # Email variables
        sender = 'noreply@syntify.emporioanalytics.com'
        to = 'noreply@syntify.emporioanalytics.com'

        if env != 'production':
            cc = os.environ['test_email']
        else:
            if data['Country'] == 'Thailand':
                cc = 'ops_th@emporioanalytics.com'
            elif data['Country'] == 'Indonesia':
                cc = 'ops_id@emporioanalytics.com'
                if data['Agency'] == 'Reta':
                    cc = cc + ',' + 'fathimah@retaconsulting.com'
                elif data['Agency'] == 'Well-Done':
                    cc = cc + ',' + 'sutan@nsc-research.com'

        subject = "Store Onboarding | " + store_code + " | " + data['storeName']
        body = "New Store Onboarding File Attached"
        data['Store Code'] = store_code

        # Create new Excel File
        df = pd.DataFrame(data, index=[0])
        df.to_excel('/tmp/onboarding.xlsx', sheet_name='Data', index=False)

        # Create a multipart message and set headers
        message = MIMEMultipart()
        message["From"] = sender
        message["To"] = to
        message["Subject"] = subject
        message["Bcc"] = cc  # Recommended for mass emails

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        filename = '/tmp/onboarding.xlsx'

        # Open PDF file in binary mode
        with open(filename, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        # Encode file in ASCII characters to send by email
        encoders.encode_base64(part)

        # Add header as key/value pair to attachment part

        part.add_header('Content-Disposition', 'attachment; filename="file.xlsx"')
        # Add attachment to message and convert message to string
        message.attach(part)
        text = message.as_string()
        context = ssl.create_default_context()

        try:
            server = smtplib.SMTP(email_server, email_port)
            server.starttls(context=context)
            server.login(email_user_id, email_password)
            server.sendmail(sender, to, text)
        except Exception as e:
            # Print any error messages to stdout
            print(e)
        finally:
            server.quit()

    send_email(fields, blank_store_code)

    if env == 'production':
        post_slack_comment(fields, blank_store_code)
    print(response)
    return response
