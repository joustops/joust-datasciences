from flask import Flask, request
import pandas as pd
import numpy as np
import distance
import json
from datetime import datetime, timedelta
from sshtunnel import SSHTunnelForwarder
import psycopg2
import math

app = Flask(__name__)

@app.route('/joustscore')
def main():
    idnum = int(request.args.get('id', None))
    score = getscore(idnum)
    joust_score = {'id':idnum, 'segment_id':score[-1], 'score':score[0]}
    
    return joust_score

def getscore(jid):
    raw = runqueries(jid)
    pre = preprocessing(raw)
    clean = processing(pre, jid)
    norm = normalize(clean)
    score = addweights(norm)
    
    return score

def runqueries(jid):
    try:
        with SSHTunnelForwarder(
            (os.environ.get('JOUST_IP'), 22),
            ssh_private_key="~/.ssh/id_rsa",
            ssh_username="ubuntu",
            remote_bind_address=(os.environ.get('JOUST_ADDRESS'), 5432)) as server:
            params = {
                "database": "joust_production",
                "user": "sid",
                "password": os.environ.get('JOUST_PASS'),
                "host": "localhost",
                "port": server.local_bind_port
            }
            conn = psycopg2.connect(**params)
            curs = conn.cursor()
            transfers = "select account_holders.id, first_name, last_name, amount, transfers.created_at as \"created_at.1\", core_pro_customers.customer_id as q2_core_pro_customer_id, from_account_id, transfers.customer_id, to_account_id from account_holders inner join transfers on account_holders.id = transfers.account_holder_id left join core_pro_customers on core_pro_customers.account_holder_id = account_holders.id where account_holders.id = " + str(jid)
            invoices = "select account_holders.id, first_name, last_name, payment_requests.status, amount, account_holders.created_at, payment_requests.created_at as \"created_at.1\", accepted_date, core_pro_customers.customer_id as q2_core_pro_customer_id, payarmour_service, payment_type from account_holders inner join payment_requests on account_holders.id = payment_requests.account_holder_id left join core_pro_customers on core_pro_customers.account_holder_id = account_holders.id where account_holders.id = " + str(jid)
            total = "select account_holders.id, account_holders.segment_intercom_id, first_name, last_name, occupations.\"name\" as occupation, industries.\"name\" as industry, marketing.value as legacy_business_url, type_of_work, locations.country, account_holders.created_at, sign_in_count, ssn, email, mobile_phone, date_of_birth, expected_yearly_income_id, core_pro_customers.customer_id as q2_core_pro_customer_id, payarmour_service from account_holders left join core_pro_customers on core_pro_customers.account_holder_id = account_holders.id left join locations on account_holders.id = locations.locatable_id left join occupations on account_holders.occupation_id = occupations.id left join industries on occupations.industry_id = industries.id left join businesses on businesses.account_holder_id = account_holders.id left join marketing on marketing.business_id = businesses.id and marketing.source = 2"
            plaid = "select account_holders.id, first_name,last_name,plaid_identities.updated_at,plaid_identities.raw_response->>'owners' from account_holders inner join external_bank_accounts on account_holders.id = external_bank_accounts.account_holder_id inner join plaid_identities on external_bank_accounts.id = plaid_identities.plaid_identifiable_id and plaid_identifiable_type='ExternalBankAccount' where account_holders.id = " + str(jid)
            bank = "select account_holders.id, first_name,last_name,bank_accounts.q2_account_id,bank_accounts.is_primary,bank_accounts.available_balance from account_holders inner join bank_accounts on bank_accounts.account_holder_id = account_holders.id where account_holders.id = " + str(jid)
            devices = "select account_holders.id, first_name, last_name, devices.signature, devices.platform, devices.created_at  from account_holders inner join account_holder_devices on account_holders.id = account_holder_devices.account_holder_id inner join devices on account_holder_devices.device_id = devices.id"
            stat = "select account_holders.id, account_holders.created_at, account_holders.archived, account_activations.status, account_holders.email, first_name, last_name, verification_status as q2_core_pro_verification_status from account_holders left join core_pro_customers on account_holders.id = core_pro_customers.account_holder_id left join account_activations on account_holders.id = account_activations.account_holder_id where account_holders.id = " + str(jid)
            events = "SELECT events.payload -> 'payloadTypeId' AS id, events.payload -> 'data' -> 0 -> 0 -> 'returnCode' AS returncode, events.payload -> 'data' -> 0 -> 0 -> 'type' AS type, events.payload -> 'data' -> 0 -> 0 -> 'amount' AS amount, events.payload -> 'data' -> 0 -> 0 -> 'customerId' AS customerId, events.payload -> 'data' -> 0 -> 0 -> 'createdDate' AS createdDate FROM \"events\""
            tra = pd.read_sql_query(transfers, conn)
            req = pd.read_sql_query(invoices, conn)
            ids = pd.read_sql_query(total, conn)
            ids.drop_duplicates(subset ="id", inplace = True)
            plaid = pd.read_sql_query(plaid, conn)
            bank = pd.read_sql_query(bank, conn)
            cells = pd.read_sql_query(devices, conn)
            rte = pd.read_sql_query(events, conn)
            status = pd.read_sql_query(stat, conn)
            conn.close()
    except Exception as e:
        print(e)
        print("Connection Failed")
    try:
        params = {
            "database": "martechdb",
            "user": "sid",
            "password": os.environ.get('MARTECH_PASS'),
            "host": os.environ.get('MARTECH_ADDRESS'),
            "port": 5439
        }
        conn = psycopg2.connect(**params)
        curs = conn.cursor()
        negative = "select * from ruby.negative_balance_alert"
        negj = pd.read_sql_query(negative, conn)
        conn.close()
    except Exception as e:
        print(e)
        print("Connection Failed")
    queries = [tra, req, ids, plaid, bank, cells, rte, status, negj]
    
    return queries


def preprocessing(queries):
    tra = queries[0]
    req = queries[1]
    ids = queries[2]
    plaid = queries[3]
    bank = queries[4]
    cells = queries[5]
    rte = queries[6]
    status = queries[7]
    negj = queries[8]
    ids = ids.rename(columns={"first_name": "First Name", "last_name": "Last Name", "type_of_work": "Type Of Work", "created_at": "Created At", "legacy_business_url": "business_url", "sign_in_count": "Sign In Count"})
    req = req.rename(columns={"first_name": "First Name", "last_name": "Last Name", "status": "Status", "amount": "Amount (Payment Requests)", "created_at": "Created At", "created_at.1": "Created At (Payment Requests)", "accepted_date": "Accepted Date", "q2_core_pro_customer_id": "Q2 Core Pro Customer Id"})
    plaid = plaid.rename(columns={"first_name": "First Name", "last_name": "Last Name", "?column?": "Raw Response"})
    tra = tra.rename(columns={"first_name": "First Name", "last_name": "Last Name", "amount": "Amount", "created_at.1": "Created At (Transfers)", "q2_core_pro_customer_id": "Q2 Core Pro Customer Id"})
    bank = bank.rename(columns={"first_name": "First Name", "last_name": "Last Name"})
    negj = negj.rename(columns={"name": "Full Name"})
    cells = cells.rename(columns={"first_name": "First Name", "last_name": "Last Name"})
    ids = ids[['id','segment_intercom_id','First Name','Last Name','ssn','email','mobile_phone','date_of_birth','business_url','occupation','industry','country','expected_yearly_income_id','q2_core_pro_customer_id','Type Of Work','Created At','payarmour_service','Sign In Count']]
    req = req[['id','First Name','Last Name','Status','Amount (Payment Requests)','Created At','Created At (Payment Requests)','Accepted Date','Q2 Core Pro Customer Id','payarmour_service','payment_type']]
    tra = tra[['id','First Name','Last Name','Amount','Created At (Transfers)','Q2 Core Pro Customer Id','from_account_id','customer_id','to_account_id']]
    negj = negj[['Full Name','balance','user_id','effective_date','type']]
    ids['Created At'] = pd.to_datetime(ids['Created At'])
    req['Created At'] = pd.to_datetime(req['Created At'])
    req['Created At (Payment Requests)'] = pd.to_datetime(req['Created At (Payment Requests)'])
    req['Accepted Date'] = pd.to_datetime(req['Accepted Date'])
    tra['Created At (Transfers)'] = pd.to_datetime(tra['Created At (Transfers)'])
    negj['effective_date'] = pd.to_datetime(negj['effective_date'])
    plaid['updated_at'] =  pd.to_datetime(plaid['updated_at'])
    ids['now'] = datetime.utcnow()
    req['now'] = datetime.utcnow()
    tra['now'] = datetime.utcnow()
    plaid['now'] = datetime.utcnow()
    req['Full Name'] = req['First Name'].astype(str).values + ' ' + req['Last Name'].astype(str).values
    req = req.drop(['First Name','Last Name'], axis=1)
    tra['Full Name'] = tra['First Name'].astype(str).values + ' ' + tra['Last Name'].astype(str).values
    tra = tra.drop(['First Name','Last Name'], axis=1)
    plaid['Full Name'] = plaid['First Name'].astype(str).values + ' ' + plaid['Last Name'].astype(str).values
    plaid = plaid.drop(['First Name','Last Name'], axis=1)
    ids['Full Name'] = ids['First Name'].astype(str).values + ' ' + ids['Last Name'].astype(str).values
    ids = ids.drop(['First Name','Last Name'], axis=1)
    bank['Full Name'] = bank['First Name'].astype(str).values + ' ' + bank['Last Name'].astype(str).values
    bank = bank.drop(['First Name','Last Name'], axis=1)
    cells['Full Name'] = cells['First Name'].astype(str).values + ' ' + cells['Last Name'].astype(str).values
    cells = cells.drop(['First Name','Last Name'], axis=1)
    tra = tra.merge(bank, how='left',left_on='id', right_on='id')
    tra['dir'] = 0
    tra['dir'] = (tra['q2_account_id'] == tra['to_account_id'])
    rte = rte.dropna()
    rte['createddate'] = pd.to_datetime(rte['createddate'])
    rte['Year'] = rte['createddate'].dt.year
    rte['Month'] = rte['createddate'].dt.month
    rte['Day'] = rte['createddate'].dt.day
    rte['Date'] = rte["Year"].astype(str) + '-' + rte["Month"].astype(str) + '-' + rte["Day"].astype(str)
    rte['Date'] = pd.to_datetime(rte['Date'])
    rcids = rte['customerid'].values
    rcodes = rte['returncode'].values
    ramounts = rte['amount'].values
    rdates = rte['Date'].values
    nsfs = pd.DataFrame(rcids, columns=['ids'])
    nsfs['code'] = rcodes
    nsfs['amount'] = ramounts
    nsfs['date'] = rdates
    nsfs['date'] = pd.to_datetime(nsfs['date'])
    nsfs['now'] = datetime.now()
    cptojid = dict(zip(ids['q2_core_pro_customer_id'], ids['id']))
    nsfs['ids'] =  nsfs['ids'].replace(cptojid)
    negj['now'] = datetime.now()
    negj['time diff'] = (negj['now'] - negj['effective_date']).dt.days
    negj = negj[negj['time diff'] < 90]
    siidtojid = dict(zip(ids['segment_intercom_id'], ids['id']))
    negj['user_id'] =  negj['user_id'].replace(siidtojid)
    ids['timediff'] = (ids['now'] - ids['Created At']).dt.total_seconds() / 3600
    req['timediff'] = (req['now'] - req['Created At (Payment Requests)']).dt.total_seconds() / 3600
    tra['timediff'] = (tra['now'] - tra['Created At (Transfers)']).dt.total_seconds() / 3600
    plaid['timediff'] = (plaid['now'] - plaid['updated_at']).dt.total_seconds() / 3600
    nsfs['timediff'] = (nsfs['now'] - nsfs['date']).dt.total_seconds() / 3600
    predata = [ids, req, tra, plaid, nsfs, negj, cells]
    
    return predata


def processing(predata, jid):
    cleandata = []
    name1 = predata[1].sort_values('Created At (Payment Requests)', ascending=True)
    name2 = predata[2].sort_values('Created At (Transfers)', ascending=True)
    name3 = predata[3].sort_values('updated_at', ascending=False)
    name4 = predata[0][predata[0]['id'] == jid]
    name6 = predata[5][predata[5]['user_id'] == jid]
    name7 = predata[6][predata[6]['id'] == jid].sort_values('created_at', ascending=False)
    atr1 = len(name1[name1['Status'] == 1])
    cleandata.append(atr1) 
    atr1_1 = 0
    if (len(name1) > 0):
        atr1_1 = len(name1[name1['Status'] == 1])/len(name1)
    cleandata.append(atr1_1)
    name1['time since start'] = name1['Created At (Payment Requests)'] - name1['Created At']
    day1t = name1[name1['time since start'] < timedelta(days=1)]
    atr2 = len(day1t)
    cleandata.append(atr2)
    atr3 = name1['Amount (Payment Requests)'].max()
    #cleandata.append(atr3)
    maxinv = 2500
    atr3_2 = 0
    if (len(name1) > 0):
        atr3_2 = len(name1[name1['Amount (Payment Requests)'] > (.95*maxinv)])/len(name1)
    cleandata.append(atr3_2)
    name1mod = name1.copy(deep=True)
    name1mod = name1mod[name1mod['Status'] == 1]
    name1mod['time diff'] = name1mod['Accepted Date'] - name1mod['Created At (Payment Requests)']
    day90 = name1mod[name1mod['time diff'] > timedelta(days=90)]
    atr5 = len(day90)
    cleandata.append(atr5)
    atr6 = len(predata[4][predata[4]['ids'] == jid])
    cleandata.append(atr6)
    atr7 = -1
    if len(name3) < 1:
        atr7 = 0
    else:
        rawres = name3['Raw Response'].values[0]
        obj = json.loads(rawres)
        bank = obj[0]['names'][0]
        real = name4['Full Name'].values[0]
        bank = bank.lower()
        real = real.lower()
        bank2 = bank.split(' ')
        if (bank2[-1] == 'llc'):
            atr7 = 0
        elif (bank2[-1] == 'jr' or bank2[-1] == 'sr' or bank2[-1] == 'jr.' or bank2[-1] == 'sr.'):
            bank = bank2[0] + ' ' + bank2[1]
            atr7 = distance.levenshtein(bank,real)
        else:
            bank = bank2[0] + ' ' + bank2[-1]
            atr7 = distance.levenshtein(bank,real)
    atr7_2 = -1
    if len(name3) < 1:
        atr7_2 = 0
    else:
        atr7_2 = 1
    cleandata.append(atr7_2)
    cleandata.append(atr7)
    atr7_3 = atr7 * atr7_2
    cleandata.append(atr7_3)
    atr8 = len(name6[name6['type'] != 'external'])
    cleandata.append(atr8)
    starttime = name4['Created At'].values[0]
    starttime = datetime.utcfromtimestamp(starttime.astype('O')/1e9)
    now = datetime.utcnow()
    acctage = (now - starttime).days
    atr10 = acctage
    cleandata.append(atr10)
    maxtra = 1500
    atr11 = name2[name2['dir'] == True]['Amount'].max()
    cleandata.append(atr11)
    atr11_2 = name2[name2['dir'] == False]['Amount'].max()
    #cleandata.append(atr11_2)
    iden = predata[0][predata[0]['Full Name'] == (predata[0][predata[0]['id'] == jid]['Full Name'].values[0])]
    ssnamount = len(iden['ssn'].unique())
    mailamount = len(iden['email'].unique())
    phoneamount = len(iden['mobile_phone'].unique())
    dobamount = len(iden['date_of_birth'].unique())
    atr12 = max([ssnamount,mailamount,phoneamount]) - 1
    cleandata.append(atr12)
    atr13 = 'no info'
    if(len(name7) > 0):
        atr13 = name7['platform'].values[0]
    #cleandata.append(atr13)
    atr13_2 = len(name7['signature'].unique())
    cleandata.append(atr13_2)
    sigs = name7['signature'].unique()
    totsigs = 0
    for k in sigs:
        totsigs = totsigs + len(predata[6][predata[6]['signature'] == k])
    atr14 = totsigs - atr13_2
    cleandata.append(atr14)
    urls = name4.dropna(subset=['business_url'])
    loc = name4['country'].unique()
    atr15 = (loc[0] == 'US')
    cleandata.append(atr15)
    atr16 = len(name6[name6['type'] == 'external'])
    cleandata.append(atr16)
    atr17 = len(urls)>0
    cleandata.append(atr17)
    atr18 = name4['industry'].values[0]
    if pd.isnull(atr18):
        atr18 = 'Other'
    d = {'Web Mobile & Software Dev':4, 'IT & Networking':4, 'Data Science & Analytics':6, 'Engineering & Architecture':6, 'Design & Creative':3, 'Translation':6, 'Legal':8, 'Admin Support':7, 'Sales & Marketing':4, 'Customer Service':7, 'Accounting & Consulting':8, 'Other':3}
    cleandata.append(d[atr18])
    atr19 = name4['occupation'].values[0]
    #cleandata.append(atr19)
    name = name4['Full Name'].values[0]
    segid = name4['segment_intercom_id'].values[0]
    caps = sum(1 for c in name if c.isupper())
    atr20 = 1
    if (len(name.replace(" ", "")) != 0):
        atr20 = caps/len(name.replace(" ", ""))
    cleandata.append(atr20)
    atr22 = name4['expected_yearly_income_id'].values[0]
    cleandata.append(atr22)
    tid = jid
    cleandata.append(tid)
    cleandata = np.nan_to_num(cleandata)
    cleandata = np.multiply(cleandata, 1) 
    cleandata = np.append(cleandata, segid)
    
    return cleandata


def normalize(cleandata):
    #here is where we can read/choose which values to include
    #here is where we can read/choose the exponents
    cleandata3 = cleandata
    cleandata2 = [float(i) for i in cleandata[:-1]]
    cleandata = cleandata2
    normdata = []
    Successful_Invoices = cleandata[0]
    Successful_Invoices = expnorm(Successful_Invoices, 0, 6, .1)
    normdata.append(Successful_Invoices)
    Invoice_Pct = cleandata[1]
    Invoice_Pct = expnorm(Invoice_Pct, 0, .8, .25)
    normdata.append(Invoice_Pct)
    First_24_Hour = cleandata[2]
    First_24_Hour = expnorm(First_24_Hour, 3, 1, .5)
    normdata.append(First_24_Hour)
    Big_Invoice_Pct = cleandata[3]
    Big_Invoice_Pct = expnorm(Big_Invoice_Pct, 1, 0, .25)
    normdata.append(Big_Invoice_Pct)
    Overdue_Invoices = cleandata[4]
    Overdue_Invoices = expnorm(Overdue_Invoices, 4, 0, 1.25)
    normdata.append(Overdue_Invoices)
    NSF_count = cleandata[5]
    NSF_count = expnorm(NSF_count, 3, 0, 1.75)
    normdata.append(NSF_count)
    Linked_Acct = cleandata[6]
    Linked_Acct = expnorm(Linked_Acct, 0, 1, 1)
    normdata.append(Linked_Acct)
    Linked_Name = cleandata[7]
    Linked_Name = expnorm(Linked_Name, 0, 1, 1.75)
    normdata.append(Linked_Name)
    Linked_Transfer = cleandata[8]
    Linked_Transfer = expnorm(Linked_Transfer, 0, 2, 2)
    normdata.append(Linked_Transfer)
    Negative_Joust = cleandata[9]
    Negative_Joust = expnorm(Negative_Joust, 1, 0, 2)
    normdata.append(Negative_Joust)
    Acct_Age = cleandata[10]
    Acct_Age = expnorm(Acct_Age, 0, 60, .75)
    normdata.append(Acct_Age)
    Biggest_Deposit = cleandata[11]
    Biggest_Deposit = expnorm(Biggest_Deposit, 1500, 1425, 1)
    normdata.append(Biggest_Deposit)
    Attempts = cleandata[12]
    Attempts = expnorm(Attempts, 2, 0, 1.25)
    normdata.append(Attempts)
    Mult_Phones = cleandata[13]
    Mult_Phones = expnorm(Mult_Phones, 2, 0, 1.5)
    normdata.append(Mult_Phones)
    Repeat_Phone = cleandata[14]
    Repeat_Phone = expnorm(Repeat_Phone, 1, 0, 1)
    normdata.append(Repeat_Phone)
    Domestic = cleandata[15]
    Domestic = expnorm(Domestic, 0, 1, 2)
    normdata.append(Domestic)
    Negative_External = cleandata[16]
    Negative_External = expnorm(Negative_External, 2, 0, .2)
    normdata.append(Negative_External)
    Website = cleandata[17]
    Website = expnorm(Website, 0, 1, 1)
    normdata.append(Website)
    Industry = cleandata[18]
    Industry = expnorm(Industry, 0, 10, .5)
    normdata.append(Industry)
    Capitals = cleandata[19]
    Capitals = expnorm(Capitals, 1, 0, .75)
    normdata.append(Capitals)
    Income = cleandata[20]
    Income = expnorm(Income, 0, 5, .1)
    normdata.append(Income)
    jid = cleandata[21]
    normdata.append(jid)
    segment = cleandata3[22]
    normdata.append(segment)
    
    return normdata


def expnorm(val, mini, maxi, exponent):
    if val > max(mini,maxi):
        val = maxi
    if val < min(mini,maxi):
        val = mini
    expval = 100 * (((val - mini)/(maxi - mini))**exponent)
    
    return expval


def addweights(normdata):
    #here is where we can read/choose the weights
    setweights = [75, 100, 25, 50, 75, 100, 50, 100, 100, 100, 75, 75, 50, 75, 100, 100, 100, 25, 75, 100, 75]
    setweights = np.array(setweights) / sum(setweights)
    score = 0
    for k in range(len(setweights)):
        score = score + (setweights[k]*normdata[k])
        
    return [score,normdata[-1]]


if __name__ == "__main__":
    app.run(debug=True)