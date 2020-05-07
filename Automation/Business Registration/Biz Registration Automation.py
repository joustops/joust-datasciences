#!/usr/bin/env python
# coding: utf-8

# In[55]:

import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

# ### Variables

# In[107]:


# replace this with user inputs in api call
BizTypeOptions = ['Limited Liability Company (Domestic)', 'Profit Corporation (Domestic)', 'Nonprofit Corporation (Domestic)', 'Nonprofit Corporation (Domestic)', 'Limited Partnership (Domestic)']
BizType = 'Limited Liability Company (Domestic)'
BizName = 'Sids Boring Test Case LLC'
AddDesignationOptions = ['Close', 'L3C', 'Processing Co-Op', 'Series', 'Series and Close']
AddDesignation = 'Close'
PerDurationChoices = ['Expires - 30 years', 'Expires - 50 years', 'Expires - 99 years', 'Perpetual']
PerDuration = 'Expires - 30 years'
FirstName = 'Sid'
LastName = 'Kannan'
AddressLine1 = '603 E Ivinson Ave'
City = 'Laramie'
Phone = '6266105295'
Email = 'sid@joust.com'
Zip = '82070'
PrinAddressLine1 = '603 E Ivinson Ave'
PrinCity = 'Laramie'
PrinState = 'WY'
PrinZip = '82070'
PrinPhone = '6266105295'
PrinEmail = 'sid@joust.com'
MailAddressLine1 = '603 E Ivinson Ave'
MailCity = 'Laramie'
MailState = 'WY'
MailZip = '82070'
# in the api, create a list and then pass
OrgFName = ['Sid']
OrgLName = ['Kannan']
Org = ['Sids Boring Test Case LLC']
OrgAddress = ['603 E Ivinson Ave Laramie, WY 82070']
AddArticlesDet = ['Your mom']
Title = 'GodMan'


# ### Start

# In[57]:


url = "https://wyobiz.wyo.gov/Business/RegistrationInstr.aspx"
driver = webdriver.Firefox()
driver.implicitly_wait(30)
driver.get(url)


# In[58]:


button = driver.find_element_by_id('regStartNow')
button.click()


# ### Type

# In[59]:


dropdown = Select(driver.find_element_by_id('MainContent_slctBusType'))
dropdown.select_by_visible_text(BizType)


# In[60]:


button = driver.find_element_by_id('MainContent_chkAgree')
button.click()


# In[61]:


button = driver.find_element_by_id('MainContent_ContinueButton')
button.click()


# ### Business Name

# In[62]:


BizName1 = driver.find_element_by_id('txtName')
BizName2 = driver.find_element_by_id('txtNameConfirm')
BizName1.send_keys(BizName)
BizName2.send_keys(BizName)


# In[63]:


dropdown = Select(driver.find_element_by_id('ddlFilingSubType'))
dropdown.select_by_visible_text(AddDesignation)


# In[64]:


button = driver.find_element_by_id('ContinueButton')
button.click()


# ### Detail

# In[65]:


# Add option to select expires and choose expiry date
dropdown = Select(driver.find_element_by_id('ddlDuration'))
dropdown.select_by_visible_text(PerDuration)


# In[66]:


#If this filing is NOT to be effective immediately, enter the effective date within the next 90 calendar days.


# In[67]:


button = driver.find_element_by_id('ContinueButton')
button.click()


# ### Agent

# In[68]:


FirstNameField = driver.find_element_by_id('txtFirstName')
LastNameField = driver.find_element_by_id('txtLastName')
AddressLine1Field = driver.find_element_by_id('txtAddr1')
CityField = driver.find_element_by_id('txtCity')
PhoneField = driver.find_element_by_id('txtPhone')
EmailField = driver.find_element_by_id('txtEmail')
FirstNameField.send_keys(FirstName)
LastNameField.send_keys(LastName)
AddressLine1Field.send_keys(AddressLine1)
CityField.send_keys(City)
PhoneField.send_keys(Phone)
EmailField.send_keys(Email)


# In[69]:


# do if statement here if mult zip screen pops up
button = driver.find_element_by_xpath('.//div[contains(@onclick, '+ str(Zip) +')]')
button.click()


# In[70]:


button = driver.find_element_by_id('chkRAConsent')
button.click()


# In[71]:


button = driver.find_element_by_id('ContinueButton')
button.click()


# In[72]:


time.sleep(2)
button = driver.find_element_by_id('ContinueButton')
button.click()
time.sleep(2)

# ### Addresses

# In[75]:


AddressLine1Field = driver.find_element_by_id('txtAddr1')
CityField = driver.find_element_by_id('txtCity')
StateField = driver.find_element_by_id('txtState')
ZipField = driver.find_element_by_id('txtPostal')
PhoneField = driver.find_element_by_id('txtPhone')
EmailField = driver.find_element_by_id('txtEmail')
AddressLine1Field.send_keys(PrinAddressLine1)
CityField.send_keys(PrinCity)
StateField.send_keys(PrinState)
ZipField.send_keys(PrinZip)
PhoneField.send_keys(PrinPhone)
EmailField.send_keys(PrinEmail)


# In[77]:


AddressLine1Field = driver.find_element_by_id('txtAddr1Mail')
CityField = driver.find_element_by_id('txtCityMail')
StateField = driver.find_element_by_id('txtStateMail')
ZipField = driver.find_element_by_id('txtPostalMail')
AddressLine1Field.send_keys(MailAddressLine1)
CityField.send_keys(MailCity)
StateField.send_keys(MailState)
ZipField.send_keys(MailZip)


# In[78]:


button = driver.find_element_by_id('ContinueButton')
button.click()


# ### Organizers

# In[99]:


# edit to work for multiple organizers
for k in range(len(OrgFName)):
    FirstNameField = driver.find_element_by_id('txtFirstName')
    LastNameField = driver.find_element_by_id('txtLastName')
    #OrgField = driver.find_element_by_id('txtOrgName')
    AddressField = driver.find_element_by_id('txtMail1')
    FirstNameField.send_keys(OrgFName[k])
    LastNameField.send_keys(OrgLName[k])
    #OrgField.send_keys(Org[k])
    AddressField.send_keys(OrgAddress[k])
    button = driver.find_element_by_id('SaveButton')
    button.click()
    time.sleep(1)


# In[100]:


button = driver.find_element_by_id('ContinueButton')
button.click()


# ### Additional Articles

# In[103]:


for k in range(len(AddArticlesDet)):
    ArtDetailField = driver.find_element_by_id('txtArticleDetail')
    ArtDetailField.send_keys(AddArticlesDet[k])
    button = driver.find_element_by_id('SaveButton')
    button.click()
    time.sleep(1)


# In[104]:


button = driver.find_element_by_id('ContinueButton')
button.click()


# ### Confirmation

# In[105]:

time.sleep(2)
button = driver.find_element_by_id('ContinueButton')
button.click()
time.sleep(2)

# ### Signature

# In[106]:


button = driver.find_element_by_id('chk1')
button.click()
button = driver.find_element_by_id('chk2')
button.click()
button = driver.find_element_by_id('chk3')
button.click()
button = driver.find_element_by_id('chk4')
button.click()
button = driver.find_element_by_id('chk5')
button.click()
button = driver.find_element_by_id('chkFalseFiling')
button.click()
button = driver.find_element_by_id('chkFilerIsInd')
button.click()


# In[108]:


FirstNameField = driver.find_element_by_id('txtFirstName')
LastNameField = driver.find_element_by_id('txtLastName')
TitleField = driver.find_element_by_id('txtTitle')
PhoneField1 = driver.find_element_by_id('txtPhone')
PhoneField2 = driver.find_element_by_id('txtPhoneConfirm')
EmailField1 = driver.find_element_by_id('txtEmail')
EmailField2 = driver.find_element_by_id('txtEmailConfirm')
FirstNameField.send_keys(FirstName)
LastNameField.send_keys(LastName)
TitleField.send_keys(Title)
PhoneField1.send_keys(Phone)
PhoneField2.send_keys(Phone)
EmailField1.send_keys(Email)
EmailField2.send_keys(Email)


# In[ ]:




