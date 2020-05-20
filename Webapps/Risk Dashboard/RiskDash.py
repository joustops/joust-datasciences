from flask import Flask, render_template, request, session
from flask_session import Session
import numpy as np
from datetime import datetime, timedelta
import distance
import pandas as pd
import json
import os
from glob import glob
import plotly
import plotly.graph_objs as go
import psycopg2
from sshtunnel import SSHTunnelForwarder


app = Flask(__name__)
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)


@app.route('/')
def startForm():
    session.clear()
    return render_template('start-form.html')


@app.route('/gawain')
def getGawain():
    alldata = loadGawData()
    neatdata = cleanGawData(alldata)
    plaiddata = neatdata[0]
    trpaydata = neatdata[1]
    plaidalerts = plaidAnalyze(plaiddata)
    trpayalerts = trpayAnalyze(trpaydata)
    alerttable = fullAlerts(plaidalerts, trpayalerts)
    return render_template('gawain.html', finalsummary=alerttable)


def loadGawData():
    try:
        with SSHTunnelForwarder(
            (os.environ.get('JOUST_IP'), 22),
            ssh_private_key="~/.ssh/id_rsa",
            ssh_username="ubuntu",
            remote_bind_address=(os.environ.get('JOUST_ADDRESS'), 5432)) as server:
            server.start()
            params = {
                "database": "joust_production",
                "user": "sid",
                "password": os.environ.get('JOUST_PASS'),
                "host": "localhost",
                "port": server.local_bind_port
            }
            conn = psycopg2.connect(**params)
            curs = conn.cursor()
            plaid = "select account_holders.id, first_name,last_name, addresses.line_1,addresses.line_2,addresses.city,addresses.state,addresses.zip,mobile_phone,email,plaid_identities.updated_at,plaid_identities.raw_response->>'owners', businesses.\"name\" from account_holders right join external_bank_accounts on account_holders.id = external_bank_accounts.account_holder_id right join plaid_identities on external_bank_accounts.id = plaid_identities.plaid_identifiable_id inner join addresses on account_holders.id = addresses.addressable_id inner join businesses on account_holders.id = businesses.account_holder_id and plaid_identifiable_type='ExternalBankAccount'"
            trpay1 = "select account_holders.id as userid, payment_requests.id, account_holders.first_name,account_holders.last_name,account_holders.email,account_holders.mobile_phone from payment_requests inner join account_holders on payment_requests.account_holder_id = account_holders.id inner join addresses on payment_requests.account_holder_id = addresses.addressable_id where addressable_type = 'AccountHolder'"
            trpay2 = "select payment_requests.id, business_entity_payers.first_name, business_entity_payers.last_name, business_entity_payers.mobile_number, business_entity_payers.email, business_entities.\"name\", business_entities.phone_number, payment_requests.created_at from payment_requests inner join business_entity_payers on payment_requests.business_entity_payer_id = business_entity_payers.id left join business_entities on business_entity_payers.business_entity_id = business_entities.id inner join addresses on payment_requests.business_entity_payer_id = addresses.addressable_id where addressable_type = 'BusinessEntity'"
            plaid = pd.read_sql_query(plaid, conn)
            trpay1 = pd.read_sql_query(trpay1, conn)
            trpay2 = pd.read_sql_query(trpay2, conn)
            conn.close()
    except Exception as e:
        print(e)
        print("Connection Failed")
    alldata = [plaid, trpay1, trpay2]
    return alldata


def cleanGawData(alldata):
    plaid = alldata[0]
    trpay1 = alldata[1]
    trpay2 = alldata[2]
    trpay = trpay1.merge(trpay2, left_on='id', right_on='id')
    trpay = trpay.fillna('')
    plaid = plaid.rename(columns={"first_name": "First Name", "last_name": "Last Name", "?column?": "Raw Response"})
    plaid['updated_at'] =  pd.to_datetime(plaid['updated_at'])
    trpay['created_at'] =  pd.to_datetime(trpay['created_at'])
    trpay['Full Name'] = trpay['first_name_y'].astype(str).values + ' ' + trpay['last_name_y'].astype(str).values
    trpay = trpay.drop(['first_name_y','last_name_y'], axis=1)
    plaid['now'] = datetime.utcnow()
    trpay['now'] = datetime.utcnow()
    plaid['timediff'] = (plaid['now'] - plaid['updated_at']).dt.total_seconds() / 3600
    trpay['timediff'] = (trpay['now'] - trpay['created_at']).dt.total_seconds() / 3600
    plaid = plaid.fillna('')
    plaid['location'] = plaid["line_1"].astype(str) + plaid["line_2"].astype(str) + ' ' + plaid["city"].astype(str) + ', ' + plaid["zip"].astype(str)
    neatdata = [plaid, trpay]
    return neatdata

def plaidAnalyze(plaiddata):
    newplaid = plaiddata
    fids = []
    ffullname = []
    fnamecheck = []
    lnamecheck = []
    fullnamecheck = []
    biznamecheck = []
    nnamedist = []
    biznamedist = []
    minnamedist = []
    statematch = []
    zipmatch = []
    emailmatch = []
    phonematch = []
    nameoncards = []
    plaiddate = []
    for npp in newplaid.values:
        pldate = npp[-6]
        plaiddate.append(pldate)
        plid = npp[0]
        plfname = npp[1].lower()
        pllname = npp[2].lower()
        ffullname.append(npp[1] + ' ' + npp[2])
        plstate = npp[6].lower()
        plzip = npp[7]
        plphone = npp[8]
        plemail = npp[9].lower()
        plcomp = npp[12].lower()
        pllocation = npp[-1]
        card = json.loads(npp[11])[0]
        cname = ''
        if (len(card['names']) > 0):
            cname = card['names'][0].lower()
        nameoncards.append(cname)
        cemail = ''
        if (len(card['emails']) > 0):
            cemail = card['emails'][0]['data'].lower()
        cstate = ''
        czip = ''
        clocation = ''
        if (len(card['addresses']) > 0):
            caddr = card['addresses'][0]['data']
            cstate = caddr['region'].lower()
            czip = caddr['postal_code']
            clocation = caddr['street'] + ' ' + caddr['city'] + ', ' + caddr['region'] + ' ' + caddr['postal_code']
        cphone = ''
        if (len(card['phone_numbers']) > 0):
            cphone = card['phone_numbers'][0]['data']
        fids.append(plid)
        fnamecheck.append(plfname in cname)
        lnamecheck.append(pllname in cname)
        biznamecheck.append((plcomp in cname) | (cname in plcomp))
        fullnamecheck.append((plfname in cname) & (pllname in cname))
        nnamedist.append(distance.levenshtein(plfname + ' ' + pllname,cname))
        biznamedist.append(distance.levenshtein(plcomp,cname))
        minnamedist.append(min(distance.levenshtein(plcomp,cname), distance.levenshtein(plfname + ' ' + pllname,cname)))
        statematch.append(plstate in cstate)
        zipmatch.append(plzip in czip)
        emailmatch.append(plemail in cemail)
        phonematch.append(plphone in cphone)
    plaidex = pd.DataFrame(fids, columns=['id'])
    plaidex['fnamecheck'] = fnamecheck
    plaidex['lnamecheck'] = lnamecheck
    plaidex['biznamecheck'] = biznamecheck
    plaidex['nnamedist'] = nnamedist
    plaidex['biznamedist'] = biznamedist
    plaidex['minnamedist'] = minnamedist
    plaidex['statematch'] = statematch
    plaidex['zipmatch'] = zipmatch
    plaidex['emailmatch'] = emailmatch
    plaidex['phonematch'] = phonematch
    plaidex = plaidex*1
    plaidex['fullname'] = ffullname
    plaidex['cardname'] = nameoncards
    plaidex['date'] = plaiddate
    evtype = []
    evtext = []
    evdate = []
    jid = []
    for pk in plaidex.values:
        if (((pk[1] == 0) | (pk[2] == 0)) & (pk[4] >= 3)):
            pmssg = (pk[-3] + ' falsely linked their account to ' + pk[-2])
            pid = (pk[0])
            pdate = (pk[-1])
            evtype.append('false linked account')
            evtext.append(pmssg)
            evdate.append(pdate)
            jid.append(pid)
    plaidalerts = [evtype, evtext, evdate, jid]
    return plaidalerts


def trpayAnalyze(trpaydata):
    trpay2 = trpaydata
    tpids = []
    tpfullnam = []
    fmat = []
    lmat = []
    mailmat = []
    phonemat = []
    tpdates = []
    for tp in trpay2.values:
        tpdate = tp[-4]
        tpdates.append(tpdate)
        tpid = tp[0]
        tpids.append(tpid)
        tpfnam = tp[2].lower()
        tplnam = tp[3].lower()
        tpfullnam.append(tp[2] + ' ' + tp[3])
        tpemail = tp[4].lower()
        tpphone = tp[5]
        cpemail = tp[7].lower()
        cpphone = tp[6]
        cpfnam = tp[-3].lower()
        fmat.append(tpfnam in cpfnam)
        lmat.append(tplnam in cpfnam)
        mailmat.append(tpemail in cpemail)
        phonemat.append(tpphone in cpphone)
    selfinv = pd.DataFrame(tpids, columns=['id'])
    selfinv['name'] = tpfullnam
    selfinv['fmat'] = fmat
    selfinv['lmat'] = lmat
    selfinv['mailmat'] = mailmat
    selfinv['phonemat'] = phonemat
    selfinv = selfinv*1
    selfinv['date'] = tpdates
    selfinv['fraud'] = selfinv['fmat'] + selfinv['lmat'] + selfinv['mailmat'] + selfinv['phonemat']
    evtype = []
    evtext = []
    evdate = []
    jid = []
    for si in selfinv[selfinv['fraud'] > 0].values:
        dupes = 'same '
        if (si[2] > 0):
            dupes = dupes + 'first name, '
        if (si[3] > 0):
            dupes = dupes + 'last name, '
        if (si[4] > 0):
            dupes = dupes + 'email, '
        if (si[5] > 0):
            dupes = dupes + 'phone, '
        smssg = (si[1] + ' has sent an invoice to themself. (' + dupes[0:-2] + ')')
        sid = (si[0])
        sdate = (si[-2])
        evtype.append('self invoice')
        evtext.append(smssg)
        evdate.append(sdate)
        jid.append(sid)
    trpayalerts = [evtype, evtext, evdate, jid]
    return trpayalerts


def fullAlerts(plaidalerts, trpayalerts):
    evtype = plaidalerts[0] + trpayalerts[0]
    evtext = plaidalerts[1] + trpayalerts[1]
    evdate = plaidalerts[2] + trpayalerts[2]
    jid = plaidalerts[3] + trpayalerts[3]
    final = pd.DataFrame(evtype, columns=['Event Type'])
    final['Event Message'] = evtext
    final['Joust ID'] = jid
    final.index = evdate
    final = final.sort_index(axis = 0, ascending=False) 
    summary = final.to_html(classes='finaltable')
    return summary



if __name__ == '__main__':
    # write comments for everything later
    app.debug = True
    app.run()