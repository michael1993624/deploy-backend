from flask import Flask, request, jsonify, send_file, redirect
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import json
from google_auth_oauthlib.flow import Flow
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
load_dotenv('.env')
from flask_cors import CORS, cross_origin
from requests_oauthlib import OAuth2Session






credentials = {
    "client_id": os.environ.get('client_id'),
    "client_secret": os.environ.get('client_secret'),
    "token_uri": os.environ.get('token_uri'),
    "developer_token": os.environ.get('developer_token'),
    "use_proto_plus" : True,
}
#Redirect URI
REDIRECT_URI = os.environ.get('redirect_uri')
FRONTEND_URI = os.environ.get('frontend_uri')

# Facebook OAuth2 configuration
FB_CLIENT_ID = os.environ.get('facebook_app_id')
FB_CLIENT_SECRET = os.environ.get('facebook_secret_key')
FB_REDIRECT_URI = os.environ.get('FB_REDIRECT_URI')
FB_AUTHORIZATION_BASE_URL = os.environ.get('FB_AUTHORIZATION_BASE_URL')
FB_TOKEN_URL = os.environ.get('FB_TOKEN_URL')

load_dotenv()
app = Flask(__name__)


CORS(app, support_credentials=True)


@app.route('/',methods=['POST'])
def index():
    req_data = request.get_json()

    default_created_at_min = (datetime.now() - timedelta(days=30)).isoformat()

    status = req_data.get('status','any')
    created_at_min = req_data.get('created_at_min',default_created_at_min)
    created_at_max = req_data.get('created_at_max', datetime.now().isoformat())
    limit = req_data.get('limit',50)

    store_url = os.getenv('STORE_URL')
    access_token = os.getenv('ACCESS_TOKEN')

    try:
        url = f'{store_url}/admin/api/2024-01/orders.json?status={status}&created_at_min={created_at_min}&created_at_max={created_at_max}&limit={limit}'
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': f'{access_token}'
        }

        response = requests.get(url, headers=headers)
        # print(response.headers)

        if response.status_code != 200:
            print(f"Error: Request failed with status code {response.status_code}")
            exit()

        data = response.json()
        orders_by_date = {}
        total_sales_by_date = {}
        total_sessions_by_date = {}
        total_orders_by_date = {}

        # Process each order
        for order in data['orders']:
            created_at = order['created_at']
            date = created_at.split('T')[0]  # Extract date from timestamp

            # Increment total sessions for the date
            total_sessions_by_date[date] = total_sessions_by_date.get(date, 0) + 1

            # Increment total sales for the date
            total_sales_by_date[date] = total_sales_by_date.get(date, 0) + float(order['total_price'])

            # Increment total orders for the date
            total_orders_by_date[date] = total_orders_by_date.get(date, 0) + 1

            # Store the order for the date
            orders_by_date.setdefault(date, []).append(order)

        # Calculate AOV for each date
        aov_by_date = {date: total_sales_by_date[date] / total_orders_by_date[date] if total_orders_by_date[date] > 0 else 0
                    for date in total_sales_by_date}

        # Prepare data for JSON output
        # output_data = [{'date': date,
        #                 'total_orders': total_orders_by_date[date],
        #                 'total_sales': total_sales_by_date[date],
        #                 'total_sessions': total_sessions_by_date[date],
        #                 'aov': aov_by_date[date]}
        #             for date in orders_by_date]
        # Output results as JSON
        # print(json.dumps(output_data, indent=2))
        #store data in csv
        import csv
        with open('shopify_data.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Day", "Orders", "total_sales", "AOV","total_sessions"])
            for date in orders_by_date:
                writer.writerow([date, total_orders_by_date[date], total_sales_by_date[date], aov_by_date[date], total_sessions_by_date[date]])
        return jsonify({'message': 'Data received successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



def get_data(customer_id,date,access_token, manager_id):
    url = f"https://googleads.googleapis.com/v16/customers/{customer_id}/googleAds:search"

    payload = "{\n\"pageSize\": 0,\n\"query\": \"\n  SELECT campaign.name,\n    campaign_budget.amount_micros,\n    campaign.status,\n    campaign.optimization_score,\n    campaign.advertising_channel_type,\n    metrics.clicks,\n    metrics.impressions,\n    metrics.ctr,\n    metrics.average_cpc,\n    metrics.cost_micros,\n    campaign.bidding_strategy_type\n  FROM campaign\n  WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'\n    AND campaign.status != REMOVED\n\"\n}"
    start_date = date
    end_date = date
    payload = payload.replace('{start_date}',start_date).replace('{end_date}',end_date)

    headers = {
      'developer-token': credentials.get('developer_token'),
      'login-customer-id': str(manager_id),
      'Content-Type': 'application/json',
      'Authorization': f'Bearer {access_token}'
      
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    # print(response.text)

    response = json.loads(response.text)

    # print(response['results'])
    try:

        sumlist = [int(i['metrics']['costMicros'])/1_000_000 for i in response['results']]

        sum_of_campaign = sum(sumlist)

        return sum_of_campaign
    except:
        result = [0]
        return result




from datetime import timedelta, date

def get_dates_between(start_date, end_date):
    """
    Get all dates between a range of dates.

    Parameters:
    - start_date (date): The start date.
    - end_date (date): The end date.

    Returns:
    - list: List of dates between the start and end dates.
    """
    dates_list = []
    current_date = start_date

    while current_date <= end_date:
        dates_list.append(current_date)
        current_date += timedelta(days=1)

    return dates_list


def convert_str_to_datetime(date_string, format_string):
    """
    Convert a string to a datetime object.

    Parameters:
    - date_string (str): The date string to be converted.
    - format_string (str): The format of the date string.

    Returns:
    - datetime: Datetime object representing the converted date.
    """
    return datetime.strptime(date_string, format_string)

# Example usage:


@app.route('/google_ads_by_id',methods=['POST'])
@cross_origin(supports_credentials=True)
def googleads(costumer_id = 4673238223,start_date=None,end_date=None):
    date_format = "%Y-%m-%d"
    manager_id = request.get_json().get('manager_id')
    customer_id = request.get_json().get('customer_id')
    print(customer_id,"vvvvvvvvvvv")
    start_date = request.get_json().get('start_date')
    end_date = request.get_json().get('end_date')


    start_date = convert_str_to_datetime(start_date, date_format)
    end_date = convert_str_to_datetime(end_date, date_format)

    print(start_date,"--")
    # access_token = request.authorization.token
    access_token = request.headers.get('Authorization')

    if costumer_id == None:
        return jsonify({"error":"Costumer id is required"})
    
    result_dates = get_dates_between(start_date, end_date)

    result = [{'date':i,'cost':(get_data(customer_id,i.strftime('%Y-%m-%d'),access_token, manager_id))} for i in result_dates]
    return result
    # costumer_id = 4673238223



@app.route('/access_token_and_refresh_token',methods=['GET'])
def access_token_and_refresh_token():
    refresh_token = request.args.get('refresh_token')
    access_token = request.args.get('access_token')
    data = {'refresh_token':refresh_token,'access_token':access_token}
    return data


@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')
    print("here")
    access = get_access_token(code)
    data = {'refresh_token':code,'access_token':access}
    urll = f'{FRONTEND_URI}/access_token_and_refresh_token?service_type=google&refresh_token={code}&access_token={access}'
    return redirect(urll)

def get_access_token(refresh_token):
    flow = Flow.from_client_secrets_file(
        './google.json',
        scopes=[
            'https://www.googleapis.com/auth/adwords',
        ],
    )
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(code=refresh_token)
    return flow.credentials.token

@app.route('/get-access-token')
def get_access_token_from_code():
    code = request.args.get('refresh_token')
    access = get_access_token(code)
    return access

@app.route('/oauth2callbackurl')
def oauth2callbackurl():
    flow = Flow.from_client_secrets_file(
        './google.json',
        scopes=[
            'https://www.googleapis.com/auth/adwords',
        ],
    )

    flow.redirect_uri = REDIRECT_URI
    # flow.run_local_server()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    print(authorization_url)
    return redirect(authorization_url)


@app.route('/get_customer')
# @cross_origin(supports_credentials=True)
def get_customer():
    refresh_token = request.headers.get('Authorization')
    if not refresh_token:
        return 'No refresh token provided', 400

        #add refresh token to credentials
    credentials['refresh_token'] = refresh_token
    client = GoogleAdsClient.load_from_dict(credentials)

    customer_service = client.get_service("CustomerService")
    customer_resource_names = (customer_service.list_accessible_customers().resource_names)
    customer_id_list = []
    googleads_service = client.get_service("GoogleAdsService")
    for customer_resource_name in customer_resource_names:
        customer_id = googleads_service.parse_customer_path(customer_resource_name)["customer_id"]
        customer_id_list.append(customer_id)

    # print("\n customer_id_list : ",customer_id_list)

    query = """
            SELECT customer_client.client_customer, customer_client.id, customer_client.manager, customer.descriptive_name, customer_client.descriptive_name FROM customer_client
            """
    # and customer.test_account != TRUE PARAMETERS include_drafts=true
    final_list = []
    for c in customer_id_list:
        try:
            response = googleads_service.search(customer_id=str(c), query=  query)
            acc = None

            final_list1 = [final_list.append({'name':d.customer_client.descriptive_name,'id':d.customer_client.id,'manager':d.customer_client.manager,'m_id':c}) for d in response]
        except:
            print("error")

    return jsonify(final_list)



# Create OAuth2 session for Facebook
def create_facebook_session(token=None, state=None, scope="ads_read"):
    return OAuth2Session(
        FB_CLIENT_ID,
        redirect_uri=FB_REDIRECT_URI,
        token=token,
        state=state,
        scope=scope
    )

@app.route('/fb/oauth2callback')
def facebookcallback():
    facebook = create_facebook_session()
    authorization_url, state = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
    print(authorization_url)
    return redirect(authorization_url)

@app.route('/facebook_callback')
def facebook_callback():
    code = request.args.get('code')
    print(code)
    facebook = create_facebook_session()
    token = facebook.fetch_token(
        FB_TOKEN_URL,
        client_secret=FB_CLIENT_SECRET,
        code=code
    )
    access_token = token.get('access_token')
    urll = f'{FRONTEND_URI}/access_token_and_refresh_token?service_type=facebook&refresh_token={code}&access_token={access_token}'
    return redirect(urll)

    


def get_fb_data(campaign_id, date, access_token):
    import requests
    from datetime import datetime
    date = date.strftime('%Y-%m-%d')

    time_range = {'since': date, 'until': date}
    time_range_str = json.dumps(time_range)
    cost = []

    url = f"https://graph.facebook.com/v19.0/{campaign_id}/insights"

    params = {
        'level': 'ad',
        'time_range': time_range_str,
        'fields': 'spend',
        'access_token': access_token
    }

    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'ps_l=0; ps_n=0'
    }

    response = requests.request("GET", url, headers=headers, params=params)
    data = response.json()
    try:
        total_spend = sum(float(entry['spend']) for entry in data['data'])
        cost.append(total_spend)
    except:
        cost.append(0)
    total_spend = sum(cost)
    return total_spend

@app.route('/get-fb-data', methods=["POST"])
def fbdata():
    date_format = "%Y-%m-%d"
    start_date = request.get_json().get('start_date')
    end_date = request.get_json().get('end_date')


    start_date = convert_str_to_datetime(start_date, date_format)
    end_date = convert_str_to_datetime(end_date, date_format)
    result_dates = get_dates_between(start_date, end_date)
    
    campaign_id = request.get_json().get('id')
    access_token = request.headers.get('Authorization')
    result_dates = get_dates_between(start_date, end_date)
    result = [{'date': date, 'cost': get_fb_data(campaign_id, date, access_token)} for date in result_dates]
    return result


def get_all_data(data):
    pagination_link = data.get('paging')
    if 'next' in pagination_link:
        next_link = pagination_link.get('next')
        response = requests.get(next_link)
        data['data'] += response.json().get('data')
        get_all_data(response.json())
    return data

@app.route('/get-fb-campaign-ids', methods=["GET"])
def get_fb_campaign_id():
    


    access_token = request.headers.get('Authorization')
    url = f"https://graph.facebook.com/v19.0/me/adaccounts?fields= business_name,account_id&access_token={access_token}&limit=100000"

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    all_data = get_all_data(response.json())

    data = all_data.get('data')
    return data


if __name__ == '__main__':
    app.run(debug=True)
