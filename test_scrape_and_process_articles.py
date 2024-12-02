import os
import unittest
from unittest.mock import patch, MagicMock
import hashlib
import datetime

# Set AWS_DEFAULT_REGION and DYNAMODB_TABLE_NAME before importing the module
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['DYNAMODB_TABLE_NAME'] = 'TestArticlesTable'

# Now import the functions to be tested
from scrape_and_process_articles import (
    scrape_bbc_news,
    process_article_with_openai,
    generate_article_id,
    store_article_in_dynamodb,
    lambda_handler  # Import lambda_handler for integration test
)

# Correct import statement for moto 5.x
from moto import mock_dynamodb
import boto3

class TestScrapeBBCNews(unittest.TestCase):
    @patch('scrape_and_process_articles.requests.get')
    def test_scrape_bbc_news(self, mock_get):
        # Mock the HTML content of the BBC News homepage with longer titles
        mock_html_content = '''
            <html>
                <body>
                    <a href="/news/123">Article Title 1 with sufficient length</a>
                    <a href="/news/456">Another Example of an Article Title</a>
                    <a href="/news/live/789">Live Article with sufficient length</a>
                    <a href="/news/av/101112">AV Article with sufficient length</a>
                </body>
            </html>
        '''
        mock_response = MagicMock()
        mock_response.content = mock_html_content.encode('utf-8')
        mock_get.return_value = mock_response

        articles = scrape_bbc_news()
        expected_articles = [
            {
                'title': 'Another Example of an Article Title',
                'url': 'https://www.bbc.com/news/456'
            },
            {
                'title': 'Article Title 1 with sufficient length',
                'url': 'https://www.bbc.com/news/123'
            }
        ]

        # Sort both lists by URL or title
        articles_sorted = sorted(articles, key=lambda x: x['url'])
        expected_articles_sorted = sorted(expected_articles, key=lambda x: x['url'])

        self.assertEqual(articles_sorted, expected_articles_sorted)


# class TestProcessArticleWithOpenAI(unittest.TestCase):
#     @patch('scrape_and_process_articles.openai.ChatCompletion.create')
#     @patch('scrape_and_process_articles.requests.get')
#     def test_process_article_with_openai(self, mock_get, mock_openai_create):
#         # Mock the article content
#         mock_html_content = '''
#             <html>
#                 <body>
#                     <article>
#                         <p>Paragraph 1.</p>
#                         <p>Paragraph 2.</p>
#                     </article>
#                 </body>
#             </html>
#         '''
#         mock_response = MagicMock()
#         mock_response.content = mock_html_content.encode('utf-8')
#         mock_get.return_value = mock_response
#
#         # Mock OpenAI API response
#         mock_openai_response = MagicMock()
#         mock_openai_response.choices = [
#             MagicMock(message=MagicMock(content='Processed AI Content'))
#         ]
#         mock_openai_create.return_value = mock_openai_response
#
#         article = {'title': 'Test Article', 'url': 'https://www.bbc.com/news/123'}
#         processed_article = process_article_with_openai(article)
#
#         self.assertIsNotNone(processed_article)
#         self.assertEqual(processed_article['title'], 'Test Article')
#         self.assertEqual(processed_article['ai_content'], 'Processed AI Content')
#         self.assertEqual(
#             processed_article['original_content'],
#             'Paragraph 1.\nParagraph 2.'
#         )
#
# class TestGenerateArticleID(unittest.TestCase):
#     def test_generate_article_id(self):
#         url = 'https://www.bbc.com/news/123'
#         expected_id = hashlib.md5(url.encode('utf-8')).hexdigest()
#         generated_id = generate_article_id(url)
#         self.assertEqual(generated_id, expected_id)
#
# class TestStoreArticleInDynamoDB(unittest.TestCase):
#     @mock_dynamodb
#     def setUp(self):
#         # Create mock DynamoDB table
#         self.dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
#         self.table = self.dynamodb.create_table(
#             TableName='TestArticlesTable',
#             KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
#             AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
#             BillingMode='PAY_PER_REQUEST'
#         )
#         self.table.meta.client.get_waiter('table_exists').wait(TableName='TestArticlesTable')
#
#     def test_store_article_in_dynamodb(self):
#         # Article to store
#         article = {
#             'id': 'test-id',
#             'title': 'Test Article',
#             'original_url': 'https://www.bbc.com/news/123',
#             'original_content': 'Original Content',
#             'ai_content': 'Processed AI Content',
#             'timestamp': datetime.datetime.utcnow().isoformat()
#         }
#
#         # Store article
#         store_article_in_dynamodb(article)
#
#         # Verify that the article was stored
#         response = self.table.get_item(Key={'id': 'test-id'})
#         self.assertIn('Item', response)
#         self.assertEqual(response['Item']['title'], 'Test Article')
#
# class TestLambdaHandlerIntegration(unittest.TestCase):
#     @mock_dynamodb
#     @patch('scrape_and_process_articles.openai.ChatCompletion.create')
#     @patch('scrape_and_process_articles.requests.get')
#     def test_lambda_handler(self, mock_get, mock_openai_create):
#         # Create mock DynamoDB table
#         dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
#         table = dynamodb.create_table(
#             TableName='TestArticlesTable',
#             KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
#             AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
#             BillingMode='PAY_PER_REQUEST'
#         )
#         table.meta.client.get_waiter('table_exists').wait(TableName='TestArticlesTable')
#
#         # Mock the HTML content of the BBC News homepage
#         mock_homepage_html = '''
#             <html>
#                 <body>
#                     <a href="/news/123">Article Title 1 with sufficient length</a>
#                 </body>
#             </html>
#         '''
#         mock_article_html = '''
#             <html>
#                 <body>
#                     <article>
#                         <p>Article content paragraph 1.</p>
#                         <p>Article content paragraph 2.</p>
#                     </article>
#                 </body>
#             </html>
#         '''
#         # Mock requests.get for homepage and article page
#         def side_effect(url, headers):
#             mock_resp = MagicMock()
#             if url == 'https://www.bbc.com/news':
#                 mock_resp.content = mock_homepage_html.encode('utf-8')
#             else:
#                 mock_resp.content = mock_article_html.encode('utf-8')
#             return mock_resp
#
#         mock_get.side_effect = side_effect
#
#         # Mock OpenAI API response
#         mock_openai_response = MagicMock()
#         mock_openai_response.choices = [
#             MagicMock(message=MagicMock(content='Processed AI Content'))
#         ]
#         mock_openai_create.return_value = mock_openai_response
#
#         # Invoke lambda_handler
#         lambda_handler({}, {})
#
#         # Verify that the article was stored
#         response = table.scan()
#         items = response.get('Items', [])
#         self.assertEqual(len(items), 1)
#         self.assertEqual(items[0]['title'], 'Article Title 1 with sufficient length')
#         self.assertEqual(items[0]['ai_content'], 'Processed AI Content')

if __name__ == '__main__':
    unittest.main()
