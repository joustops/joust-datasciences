#!/usr/bin/env python
# coding: utf-8

# In[41]:


from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
from datetime import timedelta,datetime
import glob
import shutil


# In[42]:


url = "https://xfer.propay.com/human.aspx?r=48080288&orgid=7653&rd=1"
driver = webdriver.Firefox()
driver.implicitly_wait(30)
driver.get(url)


# In[32]:


driver.fullscreen_window()


# In[43]:


username = driver.find_element_by_id('form_username') #username
password = driver.find_element_by_id('form_password') #password
username.send_keys(os.environ.get('PROPAY_USER'))
password.send_keys("PROPAY_PASS")


# In[44]:


button = driver.find_element_by_id('submit_button')
button.click()


# In[45]:


yest = datetime.utcnow() - timedelta(0)
yr = yest.year
mo = yest.month
dy = yest.day
if (mo < 10):
    mo = '0' + str(mo)
if (dy < 10):
    dy = '0' + str(dy)


# In[46]:


folderpath = '/Users/siddhesvark/Dropbox (Joust Labs, Inc.)/Customer Success/ProPay Reports/' + str(yr) + '-' + mo
isdir = os.path.isdir(folderpath)
if (isdir == False):
    os.mkdir(folderpath)


# In[47]:


folderpath2 = folderpath + '/' + str(yr) + str(mo) + str(dy)
isdir = os.path.isdir(folderpath2)
if(isdir == False):
    os.mkdir(folderpath2)


# In[ ]:


#### Downloads box blocks view. Do 4 and then 3?


# In[48]:


soup = BeautifulSoup(driver.page_source,'lxml')
soup.prettify()
name_list = soup.find_all('a', attrs={'style':'font-weight: 600;'})
filenames = [(i.contents[1].text) for i in name_list]


# In[49]:


counter = 0
for k in driver.find_elements_by_xpath("//a[starts-with(@onclick, 'return Download')]"):
    dl1 = k
    dl1.click()
    list_of_files = glob.glob('/Users/siddhesvark/Downloads/*')
    latest_file = max(list_of_files, key=os.path.getctime)
    exit = driver.find_element_by_class_name('jswiz-dialog-header-small-close-button')
    exit.click()
    shutil.move(latest_file, folderpath2 + '/' + filenames[counter])
    counter = counter + 1


# In[50]:


if len(filenames)<7:
    print('less than 7 files recieved')


# In[51]:


driver.quit()


# In[ ]:




