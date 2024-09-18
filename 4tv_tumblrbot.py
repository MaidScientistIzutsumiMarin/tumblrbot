import openai
if openai.__version__ == "0.28.0":
    print("THIS PROGRAM REQUIRES THE USE OF OPENAI API 0.28.0")
    print("To install the correct version, run the following command:")
    print("pip install openai==0.28.0")
    print("or use the included .venv")
    raise Exception("OpenAI API version must be 0.28.0")

import configparser
import pytumblr as tumblr
import argparse
import random
from halo import Halo

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Set up Tumblr client
client = tumblr.TumblrRestClient(
    config['API_KEYS']['TUMBLR_CONSUMER_KEY'],
    config['API_KEYS']['TUMBLR_CONSUMER_SECRET'],
    config['TOKENS']['TUMBLR_OAUTH_TOKEN'],
    config['TOKENS']['TUMBLR_OAUTH_TOKEN_SECRET']
)

# Read OpenAI prompt and model
SYSTEM = config['OPENAI']['SYSTEM']
PROMPT = config['OPENAI']['PROMPT']
MODEL = config['OPENAI']['MODEL']

# Set OpenAI API key
openai.api_key = config['API_KEYS']['OPENAI_API_KEY']

# Tumblr URL
TUMBLR_URL = config['TUMBLR']['TUMBLR_URL']

def generate_tags(post_content, tags_chance=0.1):
    """This function generates tags for a Tumblr post based on the content of the post.

    Arguments:
        post_content -- The content of the post for which tags are to be generated.

    Keyword Arguments:
        tags_chance -- The percent chance that tags are generated for this post (default: {0.1})

    Returns:
        list -- A list of generated tags.
        None -- If no tags are generated.
    """
    dice_roll = random.uniform(0, 1)
    if dice_roll > tags_chance:
        return None
    
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini-2024-07-18",  # Use the specified model
        messages=[
            {"role": "system", "content": "You are an advanced text summarization tool. You return the requested data to the user as a list of comma separated strings."},
            {"role": "user", "content": f"Extract the most important subjects from the following text:\n\n{post_content}"}
        ],
        max_tokens=50,
        n=1,
        stop=None,
        temperature=0.5
    )

    # Extracting the text from the model's response
    extracted_subjects = response['choices'][0]['message']['content'].strip()

    # Splitting into a list of strings
    subjects_list = extracted_subjects.split(", ")
    random.shuffle(subjects_list)
    # Limiting the number of subjects to 3
    subjects_list = subjects_list[:3]
    
    return subjects_list

def generate_text(prompt, model):
    """This function generates the actual text for a Tumblr post based on a prompt. You want to use the config model and prompt for this.

    Arguments:
        prompt -- The prompt for the model to generate text from.
        model -- The model to use for text generation.

    Returns:
        str -- The generated text.
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": prompt}],
        max_tokens=4096 - len(prompt.split())  # Adjusting for token length
    )
    return response.choices[0].message['content'].strip()

@Halo(text='Clearing drafts...', spinner='dots12')
def clear_drafts():
    """This function clears all drafts from a Tumblr blog.
    """
    # lambda draft: [client.delete_post(TUMBLR_URL, id=draft['id']) for draft in client.drafts(TUMBLR_URL)['posts']]
    # Tried a forbidden list comprehension, didn't work. Using a while loop instead.
    while len(client.drafts(TUMBLR_URL)['posts']) > 0:
        for draft in client.drafts(TUMBLR_URL)['posts']:
            client.delete_post(TUMBLR_URL, id=draft['id'])

@Halo(text='Creating drafts...', spinner='dots12')
def create_drafts(count=150, tags_chance=0.1):
    """This function creates a specified number of drafts on a Tumblr blog.

    Keyword Arguments:
        count -- The amount of posts to create (default: {150})
        tags_chance -- The rate at which those posts should be tagged (default: {0.1})
    """
    for _ in range(count):
        post_content = generate_text(PROMPT, MODEL)
        generated_tags = generate_tags(post_content, tags_chance)
        if generated_tags:
            client.create_text(TUMBLR_URL, state="draft", body=post_content, tags=generated_tags)
        else:
            client.create_text(TUMBLR_URL, state="draft", body=post_content)


def main(skip_deleting_drafts, skip_creating_drafts, draft_count, tags_chance):
    """This function is the main entry point for the script.

    Arguments:
        skip_deleting_drafts -- A command line argument to skip the deletion of drafts.
        skip_creating_drafts -- A command line argument to skip the creation of drafts.
        draft_count -- A command line argument to specify the number of drafts to create.
        tags_chance -- A command line argument to specify the chance of generating tags for a post.
    """
    if not skip_deleting_drafts:
        clear_drafts()
    if not skip_creating_drafts:
        create_drafts(draft_count, tags_chance)
    
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process command line arguments.")
    
    parser.add_argument('--skip-deleting-drafts', action='store_true', 
                        help="Skip the deletion of drafts.")
    parser.add_argument('--skip-creating-drafts', action='store_true', 
                        help="Skip the creation of drafts.")
    parser.add_argument('--draft-count', type=int, default=150, 
                        help="Number of drafts to process.")
    parser.add_argument('--tags-chance', type=float, default=0.1,
                        help="Chance of generating tags for a post.")
    
    args = parser.parse_args()
    
    main(args.skip_deleting_drafts, args.skip_creating_drafts, args.draft_count, args.tags_chance)
