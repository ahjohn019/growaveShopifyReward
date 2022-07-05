from curses import keyname
import pandas as pd
import requests
import re
import api_keys

# reading the growave csv file
gw = pd.read_csv("reward_points_june_2022_test_two.csv")

# reading the shopify csv file
sp = pd.read_csv("trans_export_one_test.csv")

# get shopify init database
API_ID = api_keys.API_ID
API_PWD = api_keys.API_PWD
SHOP_NAME = api_keys.SHOP_NAME

try:
    discountCodeApi = []
    date = "2022-06-01"
    getOrderJson = requests.get("https://"+API_ID+":"+API_PWD+"@"+SHOP_NAME +
                                "/admin/api/2021-07/orders.json?fields=id,discount_codes,name&updated_at_min=" + date + "T15:57:11-04:00&status=any&limit=250")
    for o in getOrderJson.json()['orders']:
        if(len(o['discount_codes']) > 0):
            details = {'discount_code': o['discount_codes'][0]['code'].lower(
            ), 'name': o['name'].split("#")[1]}
            discountCodeApi.append(details)

    # declare point split function
    def pointsSplits(getPoints):
        return getPoints.split()[1]

    # split the brackets in string
    def splitBrackets(points, index):
        convertPoints = points.split('(', 1)[1].split(')')[0]
        gw.loc[index, 'Coupon'] = convertPoints

    # Initialize the value
    oldOrderIndex = gw[gw['Action'].str.contains('Place')]['Action']
    containPlusPoints = gw[gw['Points'].str.contains('\+')]['Points']
    containMinusPoints = gw[gw['Points'].str.contains('-')]['Points']

    orderAppend = []

    def orderNumberPlaced():
        # 1. Extract the place order number index from action columns, update the column (done)
        for index, action in oldOrderIndex.iteritems():
            convertNumber = re.search(r'[\d]{4,5}', action)
            gw.loc[index, 'Order Name'] = convertNumber.group(0)
            orderAppend.append(convertNumber.group(0))

    def extractEarnPoints():
        # 2. Extract earn points and update to earn column
        for index, points in containPlusPoints.iteritems():
            gw.loc[index, 'Earn'] = pointsSplits(points)

    def extractCoupon():
        # 3. Extract the coupon number and minus from the flexible points columns, update column
        for index, points in containMinusPoints.iteritems():
            if '(' in points and ')' in points:
                splitBrackets(points, index)

            gw.loc[index, 'Spend'] = pointsSplits(points)

    def getStringCoupon():
        # Extra. Split the string bracket if the value is string
        for index, points in gw['Points'].iteritems():
            isString = re.search('[a-zA-Z]', pointsSplits(points))
            if isString is not None:
                splitBrackets(points, index)
                gw.loc[index, 'Spend'] = None

    def matchedFlexPoints():
        # 4. Match the flexible points (spend points) with the order api by coupon
        excludeNull = gw[gw['Coupon'].notnull()]['Coupon']
        for index, coupon in excludeNull.iteritems():
            getCouponFiltered = list(filter(
                lambda discount: discount['discount_code'] == coupon.lower(), discountCodeApi))
            if getCouponFiltered:
                gw.loc[index, 'Order Name'] = getCouponFiltered[0]['name']
                orderAppend.append(getCouponFiltered[0]['name'])

    def migrateData():
        # 5. Migrate data from reward points to shopify existing file
        for index, name in sp['Name'].iteritems():
            splitName = name.split('#')[1]
            if splitName in orderAppend:
                extraAction = len(gw.loc[gw['Order Name']
                                  == splitName]['Action'].values)
                matchOrder = gw.loc[gw['Order Name']
                                    == splitName]
                for action in matchOrder['Action'].values:
                    if(extraAction > 1):
                        sp.loc[index, 'Extra Action'] = matchOrder['Action'].values[0]
                    sp.loc[index, 'Action'] = action

                for earn in matchOrder['Earn'].values:
                    if(extraAction > 1):
                        sp.loc[index, 'Spend'] = matchOrder['Spend'].values[1]
                    sp.loc[index, 'Earn'] = earn

                for spend in matchOrder['Spend'].values:
                    if(extraAction > 1):
                        sp.loc[index, 'Earn'] = matchOrder['Earn'].values[0]
                    sp.loc[index, 'Spend'] = spend

    orderNumberPlaced()
    extractEarnPoints()
    extractCoupon()
    getStringCoupon()
    matchedFlexPoints()
    migrateData()

    sp.to_csv("trans_export_one_test.csv", index=False)
    gw.to_csv("reward_points_june_2022_test_two.csv", index=False)
    print('Export Successfully')
    print(sp)

except Exception as e:
    print(e)
    pass

# for list in matchOrder:
#                    if(extraAction > 1):
#                         if list == 'Earn':
#                             sp.loc[index, 'Spend'] = matchOrder['Spend'].values[1]
#                         if list == 'Spend':
#                             sp.loc[index, 'Earn'] = matchOrder['Earn'].values[0]
#                     else:
#                         if list != 'Order Name' and list != 'Points' and list != 'Date' and list != 'Action' and list != 'Coupon':
#                             sp.loc[index, list] = matchOrder[list].values[0]
