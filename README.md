# tumblrbot

[tumblrbot.exe]: https://github.com/MaidScientistIzutsumiMarin/tumblrbot/releases/latest/download/tumblrbot.exe

[OAuth]: https://oauth.net/1
[Python]: https://python.org/download

[JSON Lines]: https://jsonlines.org
[JSON Lines Validator]: https://jsonlines.org/validator

[pip]: https://pypi.org
[Rich]: https://pypi.org/project/rich

[OpenAI]: https://pypi.org/project/openai
[OpenAI Pricing]: https://platform.openai.com/docs/pricing#fine-tuning
[OpenAI Tokens]: https://platform.openai.com/settings/organization/api-keys
[OpenAI Moderation API]: https://platform.openai.com/docs/guides/moderation
[Flags]: https://platform.openai.com/docs/guides/moderation/over#content-classifications
[Fine-Tuning Portal]: https://platform.openai.com/finetune

[Tumblr]: https://tumblr.com
[Tumblr Tokens]: https://tumblr.com/oauth/apps
[Tumblr API Documentation on Blog Identifiers]: https://tumblr.com/docs/en/api/v2#blog-identifiers
[Tumblr API Documentation on Rate Limits]: https://tumblr.com/docs/en/api/v2#rate-limits

[Format String]: https://docs.python.org/3/library/string.html#format-string-syntax

[Download]: src/tumblrbot/flow/download.py
[Examples]: src/tumblrbot/flow/examples.py
[Fine-Tune]: src/tumblrbot/flow/fine_tune.py
[Generate]: src/tumblrbot/flow/generate.py
[Main]: src/tumblrbot/__main__.py

[Configurable]: #configuration
[Fine-Tuning]: #manual-fine-tuning
[![PyPI - Version](https://img.shields.io/pypi/v/tumblrbot)](https://python.org/pypi/tumblrbot)

Description of original project:
> 4tv-tumblrbot was a collaborative project I embarked on with my close friend Dima, who goes by @smoqueen on Tumblr. The aim of this endeavor was straightforward yet silly: to develop a Tumblr bot powered by a machine-learning model. This bot would be specifically trained on the content from a particular Tumblr blog or a selected set of blogs, allowing it to mimic the style, tone, and thematic essence of the original posts.

This fork is largely a rewrite of the source code with similarities in its structure and process.

Features:

- An [interactive console][Main] for all steps of generating posts for the blog:
   1. Asks for [OpenAI] and [Tumblr] tokens.
   1. Retrieves [Tumblr] [OAuth] tokens.
   1. [Downloads posts][Download] from specified blogs ([configurable]).
      - Skips redownloading already downloaded posts.
      - Shows progress and previews the current post.
   1. [Creates examples][Examples] to fine-tune the model from the downloaded posts.
      - Filters out posts that contain more than just text data.
      - Filters out posts that contain regular expressions ([configurable]).
      - Only uses the most recent posts from each blog ([configurable]).
      - Adds custom user messages and assistant responses to the dataset ([configurable]).
   1. Filters out any posts flagged by the [OpenAI Moderation API].
   1. [Uploads examples][Fine-Tune] to [OpenAI] and begins the fine-tuning process.
      - Provides cost estimates if the currently saved examples are used to fine-tune a base model ([configurable]).
      - Resumes monitoring the same fine-tuning process when restarted.
      - Deletes the uploaded examples file if fine-tuning does not succeed (optional).
      - Stores the output model automatically when fine-tuning is completed.
   1. [Generates and uploads posts][Generate] to a blog using the fine-tuned model ([configurable]).
      - Creates tags by extracting keywords using the base model ([configurable]).
      - Uploads posts as drafts.
      - Reblogs posts from allowed blogs ([configurable]).
      - Shows progress and previews the current post.
- Colorful output, progress bars, and post previews using [rich].
- Automatically keeps the [config][configurable] file up-to-date and recreates it if missing (without overriding user settings).

**To-Do:**

- Update to Python 3.14.
- Make post generation estimated time update regularly.

**Known Issues:**

- Fine-tuning can fail after the validation phase due to the examples file not passing [OpenAI] moderation checks. There are a few workarounds for this that can be tried in combination:
  - You can retry with the same examples file. This has, on rare occasions, worked.
  - You can submit the examples file to the [OpenAI] moderation API with this program's guided prompts. This has worked consistently for our dataset, but others have reported it not being thorough enough.
  - You can use regular expressions to filter out training data in the [config][configurable]. This is more of a brute-force solution, but it can work if the other solutions do not.
  - You can try limiting your dataset by specifying fewer blogs to download from or limiting the number of posts taken from each one in the [config][configurable].
  - If all else fails, you can manually remove data from the examples file until it passes. It is unfortunately not a definitive resource, but it can help to read about what the [OpenAI moderation API flags][Flags].
- Sometimes, you will get an error about the training file not being found when starting fine-tuning. We do not currently have a fix or workaround for this. You should instead use the online portal for fine-tuning if this continues to happen. Read more in [fine-tuning].
- Post counts are incorrect when downloading posts. We are not certain what the cause of this is, but our tests suggest this is a [Tumblr] API problem that is giving inaccurate numbers.
- During post downloading or post generation, you may receive a "Limit Exceeded" error message from the [Tumblr] API. This is caused by server-side rate-limiting by [Tumblr]. The only workaround is trying again or waiting for a period of time before retrying. In most cases, you either have to wait for a minute or an hour for the limits to reset. You can read more about the limits in the [Tumblr API documentation on rate limits].
- Similar to the above issue, you may sometimes get a message saying your IP is blocked. This block is temporary and probably follows the same rules as previously described.

**Please submit an issue or contact us for features you want added/reimplemented.**

## Installation

1. Install the latest version of [Python]:
   - Windows: `winget install python3`
   - Linux (apt): `apt install python-pip`
   - Linux (pacman): `pacman install python-pip`
1. Install the [pip] package: `pip install tumblrbot`
   - Alternatively, you can install from this repository: `pip install git+https://github.com/MaidThatPrograms/tumblrbot.git`
   - On Linux, you will have to make a virtual environment or use the flag to install packages system-wide.

### Alternative Installation for Windows

1. Download the latest release's [tumblrbot.exe].
1. Run the file directly, or add it to your path, and use it as normal.

## Usage

Run `tumblrbot` from anywhere. Run `tumblrbot --help` for command-line options. Every command-line option corresponds to a value from the [config][configurable].

## Obtaining Tokens

### OpenAI

API token can be created here: [OpenAI Tokens].

   1. Leave everything at the defaults and set `Project` to `Default Project`.
   1. Press `Create secret key`.
   1. Press `Copy` to copy the API token to your clipboard.

### Tumblr

API tokens can be created here: [Tumblr Tokens].

   1. Press `+ Register Application`.
   1. Enter anything for `Application Name` and `Application Description`.
   1. Enter any URL for `Application Website` and `Default callback URL`, like `https://example.com`.
   1. Enter any email address for `Administrative contact email`. It probably doesn't need to be one you have access to.
   1. Press the checkbox next to `I'm not a robot` and complete the CAPTCHA.
   1. Press `Register`.
   1. You now have access to your `consumer key` next to `Oauth Consumer Key`.
   1. Press `Show secret key` to see your `Consumer Secret`.

When running this program, you will be prompted to enter all of these tokens. If something goes wrong while entering the tokens, you can always reset them by running the program again and answering `y` to the relevant prompt.

After inputting the [Tumblr] tokens, you will be given a URL that you need to open in your browser. Press `Allow`, then copy and paste the URL of the page you are redirected to into the console.

## Configuration

All config options can be found in `config.toml` after running the program once. This will be kept up-to-date if there are changes to the config's format in a future update. This also means it may be worthwhile to double-check the config file after an update. Any changes to the config should be in the changelog for a given version.

All file options can include directories that will be created when the program is run.

All config options that involve *blog identifiers* expect any version of a blog URL, which is explained in more detail in the [Tumblr API documentation on blog identifiers].

A valid post:

- Contains any content.
- Only has text.
- Is not an ask.
- Is not a reblog.

Specific Options:

- `custom_prompts_file` This file should follow the following file format:

   ```json
   {"user message 1": "assistant response 1"}
   {"user message 1": "assistant response 1"}
   {"user message 2": "assistant response 2", "user message 3": "assistant response 3"}
   ```

   To be specific, it should follow the [JSON Lines] file format with one collection of name/value pairs (a dictionary) per line. You can validate your file using the [JSON Lines Validator].

- **`post_limit`** - At most, this many valid posts will be included in the training data. This effectively is a filter to select the `N` most recent valid posts from each blog. `0` will use every available valid post.
- **`filtered_words`** - During training data generation, any posts with the specified words will be removed. Word boundaries are not checked by default, so "the" will also filter out posts with "them" or "thematic". This setting supports regular expressions, so you can explicitly look for word boundaries by surrounding an entry with "\\\b", i.e. "\\\bthe\\\b". Regular expressions have to be escaped like so due to how JSON data is read in. If you are familiar with regular expressions, it could be useful for you to know that every entry is joined with a "|" which is then used to search the post content for any matches.
- **`developer_message`** - This message is used in for fine-tuning the AI as well as generating prompts. If you change this, you will need to run the fine-tuning again with the new value before generating posts.
- **`user_message`** - This setting is used and works in the same way as `developer_message`.
- **`expected_epochs`** - The default value here is the default number of epochs for `base_model`. You may have to change this value if you change `base_model`. After running fine-tuning once, you will see the number of epochs used in the [fine-tuning portal] under *Hyperparameters*. This value will also be updated automatically if you run fine-tuning through this program.
- **`token_price`** - The default value here is the default token price for `base_model`. You can find the up-to-date value in [OpenAI Pricing], in the *Training* column.
- **`job_id`** - If there is any value here, this program will resume monitoring the corresponding job, instead of starting a new one. This gets set when starting the fine-tuning and is cleared when it is completed. You can read more in [fine-tuning].
- **`base_model`** - This value is used to choose the tokenizer for estimating fine-tuning costs. It is also the base model that will be fine-tuned and the model that is used to generate tags. You can find a list of options in the [fine-tuning portal] by pressing `+ Create` and opening the drop-down list for `Base Model`. Be sure to update `token_price` if you change this value.
- **`fine_tuned_model`** - Set automatically after monitoring fine-tuning if the job has succeeded. You can read more in [fine-tuning].
- **`tags_chance`** - This should be between 0 and 1. Setting it to 0 corresponds to a 0% chance (never) to add tags to a post. 1 corresponds to a 100% chance (always) to add tags to a post. Adding tags incurs a very small token cost.
- **`reblog_blog_identifiers`** - Whenever a reblog is attempted, a random blog from this list will be chosen to be reblogged from.
- **`reblog_chance`** - This setting works the same way as `tags_chance`.
- **`reblog_user_message`** - This setting is a [format string]. The only argument it is formatted with is the content of the post being reblogged. In simple terms, the `{}` will be replaced with said content. Alternatively, you can leave out the `{}` so that the reblogged post is appended to the end.
  - *Note: The bot is only given the latest message in a reblog chain due to the required complexity and added costs of including the entire chain.*

## Manual Fine-Tuning

You can manually upload the examples file to [OpenAI] and start the fine-tuning here: [fine-tuning portal].

1. Press `+ Create`.
1. Select the desired `Base Model` from the dropdown. This should ideally match the model set in the [config][configurable].
1. Upload the generated examples file to the section under `Training data`. You can find the path for this in the [config][configurable].
1. Press `Create`.
1. (Optional) Copy the value next to `Job ID` and paste it into the [config][configurable] under `job_id`. You can then run the program and monitor its progress as usual.
1. If you do not do the above, you will have to copy the value next to `Output model` once the job is complete and paste it into the [config][configurable] under `fine_tuned_model`.
