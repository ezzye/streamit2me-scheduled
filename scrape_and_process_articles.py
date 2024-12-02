import os
import boto3
import requests
from bs4 import BeautifulSoup
import openai
import datetime
import hashlib
import logging

# Step 1: Set the AWS_DEFAULT_REGION before importing the module
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'  # You can choose any valid AWS region

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE_NAME')
table = dynamodb.Table(table_name)

# Set OpenAI API key
openai.api_key = os.environ.get('OPENAI_API_KEY')

def lambda_handler(event, context):
    try:
        # Scrape BBC News articles
        articles = scrape_bbc_news()

        # Process and store each article
        for article in articles:
            processed_article = process_article_with_openai(article)
            if processed_article:
                store_article_in_dynamodb(processed_article)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")

def scrape_bbc_news():
    logger.info("Scraping BBC News website")
    url = 'https://www.bbc.com/news'
    headers = {
        'User-Agent': 'YourAppName/1.0'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    articles = []
    # Find article links
    for item in soup.find_all('a', href=True):
        link = item['href']
        if '/news/' in link and 'live' not in link and 'av/' not in link:
            full_link = 'https://www.bbc.com' + link if link.startswith('/') else link
            title = item.get_text(strip=True)
            if title and full_link and len(title) > 20:
                articles.append({
                    'title': title,
                    'url': full_link
                })

    # Remove duplicates
    articles = [dict(t) for t in {tuple(d.items()) for d in articles}]
    logger.info(f"Found {len(articles)} articles")
    return articles

def process_article_with_openai(article):
    logger.info(f"Processing article: {article['title']}")
    # Fetch the article content
    headers = {
        'User-Agent': 'YourAppName/1.0'
    }
    response = requests.get(article['url'], headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract article content
    content = ''
    article_body = soup.find('article')
    if article_body:
        paragraphs = article_body.find_all('p')
        content = '\n'.join([p.get_text() for p in paragraphs])
    else:
        # Try alternative method
        paragraphs = soup.find_all('p')
        content = '\n'.join([p.get_text() for p in paragraphs])

    if not content.strip():
        logger.warning(f"No content found for article: {article['title']}")
        return None

    # Prepare the prompt for OpenAI
    prompt = f"""
Please analyze the following BBC News article for bias and impartiality. Point out any weaknesses, suggest improvements, and provide an expanded or revised version of the article that addresses these issues.

Article Title: {article['title']}

Article Content:
{content}
"""

    try:
        response = openai.ChatCompletion.create(
            model="o1-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        ai_content = response.choices[0].message.content
        logger.info(f"Received AI content for article: {article['title']}")
        processed_article = {
            'id': generate_article_id(article['url']),
            'title': article['title'],
            'original_url': article['url'],
            'original_content': content,
            'ai_content': ai_content,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        return processed_article
    except Exception as e:
        logger.error(f"Error processing article with OpenAI: {str(e)}")
        return None

def store_article_in_dynamodb(article):
    try:
        table.put_item(Item=article)
        logger.info(f"Stored article in DynamoDB: {article['title']}")
    except Exception as e:
        logger.error(f"Error storing article in DynamoDB: {str(e)}")

def generate_article_id(url):
    # Generate a unique ID using MD5 hash of the URL
    return hashlib.md5(url.encode('utf-8')).hexdigest()
