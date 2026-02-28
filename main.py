import os
import re
import asyncio
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv
from telethon import TelegramClient, events
from supabase import create_client, Client

# Load environment variables
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE_NUMBER = os.getenv('TELEGRAM_PHONE_NUMBER')
CHANNELS = os.getenv('CHANNELS_TO_LISTEN', '').split(',')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
AMAZON_TAG = os.getenv('AMAZON_AFFILIATE_TAG')
FLIPKART_TAG = os.getenv('FLIPKART_AFFILIATE_TAG')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Telegram client
client = TelegramClient('deal_aggregator_session', API_ID, API_HASH)

def modify_affiliate_link(url, platform):
    """Appends affiliate tags to the URL."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    if platform == 'Amazon' and AMAZON_TAG:
        query_params['tag'] = [AMAZON_TAG]
    elif platform == 'Flipkart' and FLIPKART_TAG:
        query_params['affid'] = [FLIPKART_TAG]
        
    # Reconstruct the URL with new query parameters
    new_query = urlencode(query_params, doseq=True)
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    return new_url

def parse_message(text):
    """Parses Telegram message text using regex to extract deal data."""
    deal = {
        'product_name': 'Unknown Product',
        'deal_price': None,
        'original_price': None,
        'link': None,
        'card_offer': None,
        'platform': 'Unknown',
        'category': 'uncategorized'
    }
    
    # Extract Link
    link_match = re.search(r'(https?://[^\s]+)', text)
    if link_match:
        deal['link'] = link_match.group(1).rstrip('.').rstrip(')')
        if 'amzn' in deal['link'] or 'amazon' in deal['link'].lower():
            deal['platform'] = 'Amazon'
        elif 'flipkart' in deal['link'].lower() or 'fkrt' in deal['link'].lower():
            deal['platform'] = 'Flipkart'
            
    # Extract Prices (looking for ₹ followed by numbers/commas)
    prices = re.findall(r'₹([\d,]+)', text)
    if len(prices) >= 1:
        deal['deal_price'] = float(prices[0].replace(',', ''))
    if len(prices) >= 2:
        deal['original_price'] = float(prices[1].replace(',', ''))
        
    # Extract Product Name (heuristic: text between emojis or before "is now just")
    name_match = re.search(r'(?:🔥.*?🔥)?\s*(.*?)\s+(?:is now just|at ₹)', text, re.IGNORECASE)
    if name_match:
        deal['product_name'] = name_match.group(1).strip()
    else:
        # Fallback: take first line if it's not too long
        first_line = text.split('\n')[0].strip()
        if len(first_line) < 100:
            deal['product_name'] = first_line
        
    # Extract Card Offer
    offer_match = re.search(r'(Get extra.*?Card|Bank Offer:.*?)', text, re.IGNORECASE)
    if offer_match:
        deal['card_offer'] = offer_match.group(1).strip()
        
    # Modify link if found
    if deal['link']:
        deal['link'] = modify_affiliate_link(deal['link'], deal['platform'])
        
    return deal

@client.on(events.NewMessage(chats=CHANNELS))
async def handler(event):
    """Handles new messages from the specified Telegram channels."""
    text = event.raw_text
    print(f"New message received: {text[:50]}...")
    
    deal_data = parse_message(text)
    
    if deal_data['link'] and deal_data['deal_price']:
        try:
            # Insert into Supabase
            response = supabase.table('deals').insert(deal_data).execute()
            print(f"Successfully inserted deal: {deal_data['product_name']}")
        except Exception as e:
            print(f"Error inserting deal to Supabase: {e}")
    else:
        print("Message did not contain a valid deal. Skipping.")

async def main():
    print("Starting Telegram Listener...")
    await client.start(phone=PHONE_NUMBER)
    print("Listener is running. Press Ctrl+C to stop.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
