import os
from dataclasses import dataclass, asdict
from datetime import datetime
from bs4 import BeautifulSoup
import configparser
import re
import random
import nltk
from nltk.corpus import wordnet as wn
from nltk import pos_tag, word_tokenize
import json
import tiktoken
from halo import Halo

# Load the special words from the JSON file. Special words are used to replace nouns, verbs, and adjectives in the training data at a certain rate. 
# This is done to intentionally inject particular words into the training data to influence the model's output to overrepresent certain concepts.
# In the case of dimabot, this was some stuff about mummies. dr. jekyll and mr. hyde, and tigermen. 
with open('special_words.json', 'r') as file:
    special_words = json.load(file)

# Load the configuration file
# It's a shared configuration file for all the scripts in this project
# Kinda ugly, but I found it to be most visually appealing to have all the configuration in one place
config = configparser.ConfigParser()
config.read('config.ini')

# Load the system and prompt messages from the configuration file
SYSTEM = config['OPENAI']['SYSTEM']
PROMPT = config['OPENAI']['PROMPT']
# Load the maximum year from the configuration file. This is used to filter out posts from before a certain year.
MAX_YEAR = int(config['TUMBLR']['MAX_YEAR'])

# Initialize the list of posts to store the parsed post data as TumblrPost objects
posts = []


# Define a dataclass to represent a Tumblr post
# We are only interested in a subset of the fields in the post data for our training data
# If you want to include more fields, you can add them to the dataclass and the regular expression in the parse_post_data function
@dataclass
class TumblrPost:
    type: str
    id: int
    timestamp: datetime
    post_url: str
    slug: str
    reblog_key: str
    reblog_url: str
    reblog_name: str
    title: str
    body: str
    question: str
    answer: str
    link: str
    quotes: str
    quote_source: str
    tags: list
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
@Halo(text='Downloading NLTK resources', spinner='dots12')
def download_nltk_resources():
    """Download the necessary NLTK resources for tokenization, POS tagging, and wordnet lemmatization."""
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('averaged_perceptron_tagger_eng')
    nltk.download('wordnet')

def remove_html_tags(html_string):
    """Remove HTML tags from the input string.

    Arguments:
        html_string -- The input string to process, which is a Tumblr post body or title.

    Returns:
        The input string with HTML tags removed.
    """
    # Create a BeautifulSoup object from the HTML string
    soup = BeautifulSoup(html_string, "html.parser")

    # Extract the plain text
    plain_text = soup.get_text()

    return plain_text

def remove_usernames(input_string):
    """Remove usernames from the input string.

    Arguments:
        input_string -- The input string to process, which is a pre-scrubbed Tumblr post body.

    Returns:
        The input string with username prefixes removed.
    """
    # Define the pattern to match {username}: at the start of the string
    pattern = r'^(?:[a-z0-9-]+:)+'
    
    # Use re.sub to replace the matched pattern with an empty string
    return re.sub(pattern, '', input_string)

def sanitize(input_string):
    """Sanitize the input string by escaping special characters.

    Arguments:
        input_string -- The input string to sanitize, which is a pre-scrubbed Tumblr post body.

    Returns:
        The sanitized input string with special characters escaped.
    """
    return input_string.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ").replace("\r", " ").replace("\t", " ")

@Halo(text='Parsing post data...', spinner='dots12')
def parse_post_data(file_path, file_type):
    """Parse the Tumblr post data from the specified file.

    Arguments:
        file_path -- The path to the file containing the Tumblr post data.
        file_type -- The type of Tumblr post data in the file.

    Returns:
        A list of TumblrPost objects representing the parsed post data.
    """
    with open(file_path, 'r') as file:
        data = file.read()

    # Split the file content into individual posts
    raw_posts = data.strip().split('\n\n')

    posts = []
    post_pattern = re.compile(
        r'Post id:\s*(?P<post_id>\d+)\n'
        r'Date:\s*(?P<date>.+)\n'
        r'Post url:\s*(?P<post_url>.+)\n'
        r'Slug:\s*(?P<slug>.*)\n'
        r'Reblog key:\s*(?P<reblog_key>.*)\n'
        r'Reblog url:\s*(?P<reblog_url>.*)\n'
        r'Reblog name:\s*(?P<reblog_name>.*)\n'
        r'Title:\s*(?P<title>.*)\n'
        r'Body:\s*(?P<body>(?:.|\n)*?)\n(?=Tags:|$)'
        r'Tags:\s*(?P<tags>.*)?'
    )

    for raw_post in raw_posts:
        match = post_pattern.search(raw_post)
        if match:
            # Gather the post data from the match
            post_data = match.groupdict()
            
            # Convert fields to the appropriate types
            post_id = int(post_data['post_id'])
            timestamp = datetime.strptime(post_data['date'], '%Y-%m-%d %H:%M:%S %Z')
            tags = post_data['tags'].split(', ') if post_data['tags'] else []
            body = post_data['body'].strip()
            title = post_data['title'].strip()
            
            # You definitely want to remove usernames, as they are not relevant to the training data and cause many issues.
            body = remove_usernames(body)
            
            # Remove newlines from the body
            # This is done to ensure that the training data is formatted correctly. Each message should be on a single line. 
            # You might be able to escape the newlines instead but I didn't have any luck doing that myself.
            body = body.replace('\n', ' ')

            # Create a TumblrPost object
            # As you can see, we are not interested in a number of fields. If you want to use them, you can add them to the regular expression above.
            post = TumblrPost(
                type=file_type,
                id=post_id,
                timestamp=timestamp,
                post_url=post_data['post_url'],
                slug=post_data['slug'],
                reblog_key=post_data['reblog_key'],
                reblog_url=post_data['reblog_url'],
                reblog_name=post_data['reblog_name'],
                title=title,
                body=body,
                question='',
                answer='',
                link='',
                quotes='',
                quote_source='',
                tags=tags
            )

            posts.append(post)

    return posts

def parse_files():
    """Parse the Tumblr post data files in the 'data' directory.

    Raises:
        FileNotFoundError: If the 'data' directory does not exist.
        FileNotFoundError: If no data files are found.
        ValueError: If the post type in the data file name is not one of 'texts', 'answers', 'links', 'conversations', or 'quotes', or otherwise only malformed files exist.
    """
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Check if any files exist in the 'data' directory
    files = os.listdir('data')
    if len(files) == 0:
        raise FileNotFoundError("No data files found in the 'data' directory.")
    
    # Check if any of the files match the expected naming convention
    file_name_format = re.compile(r"(.*)?_(texts|answers|links|conversations|quotes)\.txt")
    
    matches = False
    for file in files:
        match = file_name_format.match(file)
        if match:
            matches = True
            break
        
    if not matches:
        raise ValueError("No data files found with the correct naming convention. The file name format should be 'blogname_posttype.txt', and the post type should be one of 'texts', 'answers', 'links', 'conversations', or 'quotes'. Please place the data files in the 'data' directory and try again.")
        
    # Parse the post data from the files
    for file in files:
        # File name format is blogname_type.txt!! You MUST follow this format
        tumblr_type = file.split('_')[1].split('.')[0]
        match tumblr_type:
            case "texts":
                parsed_data = parse_post_data("data/" + file, tumblr_type)
                # We use extend here because parsed_data is a list of posts, and ideally we like to modify lists in place
                posts.extend(parsed_data)
            case "answers":
                print(f"For {file}, Answer posts are not supported at this time.")
            case "conversations":
                print(f"For {file}, Conversation posts are not supported at this time.")
            case "links":
                print(f"For {file}, Link posts are not supported at this time.")
            case "quotes":
                print(f"For {file}, Quote posts are not supported at this time.")
            case _:
                print(f"Unknown file type {file}")

@Halo(text='Calculating tokens & writing output...', spinner='dots12')
def write_output():
    """Write the training data to the output files. The training data consists of a JSONL file with the system, user, and assistant messages for each post.

    Returns:
        The total number of words in the training data files.
    """
    if not os.path.exists('output'):
        os.makedirs('output')
        
    # I have found that leaving the HTML tags *can* work, but it's better to remove them
    # if you just want a consistent output.
    # Either way, I have included both options here.
    # The no_html files are the ones that have the HTML tags removed.
    # The originals_only files are the ones that are original posts only.
    with open('output/training.jsonl', 'w', encoding="utf-8") as file:
        with open('output/training_originals_only.jsonl', 'w', encoding="utf-8") as file_originals:
            with open('output/training_no_html.jsonl', 'w', encoding="utf-8") as file_no_html:
                with open('output/training_no_html_originals_only.jsonl', 'w', encoding="utf-8") as file_no_html_originals:
                    words = 0
                    words_originals = 0
                    for post in posts:
                        if post.timestamp.year < MAX_YEAR:
                            # Skip posts from before the specified year
                            continue
                        dice_roll = random.uniform(0, 1)
                        if dice_roll < 0.01:
                            # For 1% of posts, we replace some amount of nouns, verbs, and adjectives with special words.
                            # I found that 1% was a good balance for my purposes, but you can adjust this as needed.
                            # I have chosen to omit this from the config as it's a bit more advanced and not necessary for most users.
                            # And also requires a lot of fine-tuning to get right.
                            post_body_no_html = replace_special_words(remove_html_tags(post.body), special_words)
                            post_body = replace_special_words(post.body, special_words)
                        else:
                            post_body = post.body
                            post_body_no_html = remove_html_tags(post_body)
                        if post_body == "":
                            # Skip posts without a body
                            continue
                        # Create the appropriate JSONL data for the post
                        data = "{\"messages\": [{\"role\": \"system\", \"content\": \"" + SYSTEM + "\"}, {\"role\": \"user\", \"content\": \""+ PROMPT +"\"}, {\"role\": \"assistant\", \"content\": \"" + sanitize(post_body) +"\"}]}"+ '\n'
                        file.write(data)
                        if post_body_no_html != "":
                            data_no_html = "{\"messages\": [{\"role\": \"system\", \"content\": \"" + SYSTEM + "\"}, {\"role\": \"user\", \"content\": \""+ PROMPT +"\"}, {\"role\": \"assistant\", \"content\": \"" + sanitize(post_body_no_html) +"\"}]}"+ '\n'
                            file_no_html.write(data_no_html)
                        # This is a very rough way of counting words, but it should be good enough for our purposes
                        words += count_tokens(SYSTEM + " " + PROMPT + " " + post.body)
                        if post.reblog_url == "" and post.reblog_name == "":
                            # Kind of a hack way to determine if the post is original, but it worked for 100% of the 300,000 posts I tested, so it should be good enough.
                            file_originals.write(data)
                            if post_body_no_html != "":
                                file_no_html_originals.write(data_no_html)
                            words_originals += count_tokens(SYSTEM + " " + PROMPT + " " + post.body)
    return words, words_originals


def get_wordnet_pos(treebank_tag):
    """This is a helper function to convert NLTK POS tags to WordNet POS tags.
    This is used in the replace_special_words function to identify nouns, verbs, and adjectives.

    Arguments:
        treebank_tag -- The NLTK POS tag to convert.

    Returns:
        The corresponding WordNet POS tag or None if no conversion is found.
    """
    if treebank_tag.startswith('J'):
        return wn.ADJ
    elif treebank_tag.startswith('V'):
        return wn.VERB
    elif treebank_tag.startswith('N'):
        return wn.NOUN
    elif treebank_tag.startswith('R'):
        return wn.ADV
    else:
        return None


def replace_special_words(input_string, special_words):
    """Replace nouns, verbs, and adjectives in the input string with special words from the provided dictionary.
    We only replace words with a 10% probability, as we don't want to overdo it. This leads to .1% of words being replaced in the training data.
    We use the NLTK library to tokenize the input string and identify the parts of speech of the words.
    Arguments:
        input_string -- The input string to process.
        special_words -- A dictionary containing special words for nouns, verbs, and adjectives.

    Returns:
        The modified input string with nouns, verbs, and adjectives replaced by special words.
    """
    # Tokenize the input string and get the parts of speech
    words = word_tokenize(input_string)
    pos_tags = pos_tag(words)

    # Identify nouns, verbs, adjectives using WordNet
    words_to_replace = {
        'noun': [],
        'verb': [],
        'adjective': []
    }
    
    for word, pos in pos_tags:
        wordnet_pos = get_wordnet_pos(pos)
        if wordnet_pos == wn.NOUN:
            words_to_replace['noun'].append(word)
        elif wordnet_pos == wn.VERB:
            words_to_replace['verb'].append(word)
        elif wordnet_pos == wn.ADJ:
            words_to_replace['adjective'].append(word)

    # Replace nouns, verbs, adjectives with entries from special_words
    for category in ['noun', 'verb', 'adjective']:
        if category in special_words:
            for word in words_to_replace[category]:
                if special_words.get(category):
                    dice_roll = random.uniform(0, 1)
                    if dice_roll < 0.1:
                        idx = words.index(word)
                        words[idx] = random.choice(special_words[category])

    # Return the modified sentence
    return ' '.join(words)

def count_tokens(input_string):
    # Initialize the tokenizer for the 'cl100k_base' model
    # This is the same tokenizer that is used in the OpenAI GPT-4 model which is the model I used for dimabot
    tokenizer = tiktoken.get_encoding("cl100k_base")
    
    # Encode the input string to get the tokenized result
    tokens = tokenizer.encode(input_string)
    
    # Return the number of tokens
    return len(tokens)

                    
def main():
    download_nltk_resources()
    parse_files()
    words, words_originals = write_output()
    print(f"Processed {len(posts):,} posts")
    print(f"Total tokens: {words:,}")
    print(f"Total tokens in originals: {words_originals:,}")
    # Cost of gpt-4o-mini at time of writing is 30 cents per 1,000,000 tokens
    print(f"Expected cost for all posts when trained with gpt-4o-mini: ${words / 1000000 * 0.3:.2f}")
    print(f"Expected cost for original posts when trained with gpt-4o-mini: ${words_originals / 1000000 * 0.3:.2f}")
    print("NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.")
    print("      Amelia is not responsible for any inaccuracies in the token count or estimated price.\n")
    print("The training data has been written to the 'output' directory.")
    
    
if __name__ == "__main__":
    main()
