# tumblrbot

[pip]: https://github.com/pypa/pip
[uv]: https://github.com/astral-sh/uv

[Python Installation]: https://docs.python.org/3/installing
[Format String]: https://docs.python.org/3/library/string.html#format-string-syntax

[uv Installation]: https://docs.astral.sh/uv/getting-started/installation
[uv Tools]: https://docs.astral.sh/uv/guides/tools

[OAuth]: https://oauth.net/1

[JSON Lines]: https://jsonlines.org
[JSON Lines Validator]: https://jsonlines.org/validator

[OpenAI]: https://openai.com
[OpenAI Pricing]: https://platform.openai.com/docs/pricing#fine-tuning
[OpenAI Tokens]: https://platform.openai.com/settings/organization/api-keys
[OpenAI Moderation API]: https://platform.openai.com/docs/guides/moderation
[Flags]: https://platform.openai.com/docs/guides/moderation#content-classifications
[Fine-Tuning Portal]: https://platform.openai.com/finetune

[Tumblr]: https://tumblr.com
[Tumblr Tokens]: https://tumblr.com/oauth/apps
[Tumblr API Documentation on Blog Identifiers]: https://tumblr.com/docs/api#blog-identifiers

[Config]: #configuration
[Manual Fine-Tuning]: #manual-fine-tuning

[regex101]: https://regex101.com

[![PyPI - Version](https://img.shields.io/pypi/v/tumblrbot)](https://python.org/pypi/tumblrbot)

## Installation & Usage

1. Install the latest version of [uv] following [these instructions][uv Installation].
1. Run `tumblrbot`:
   - Basic Usage: `uvx tumblrbot`
   - Display Help: `uvx tumblrbot --help`
   - [More Information about `uvx`.][uv Tools] This command will automatically use the latest versions of `tumblrbot` and its dependencies.

**Every command-line option corresponds to a value from the [config].**

> To use this package through [pip], follow [these instructions][Python Installation].

---

### Project Description

> [4tv-tumblrbot was a collaborative project I embarked on with my close friend Dima, who goes by @smoqueen on Tumblr. The aim of this endeavor was straightforward yet silly: to develop a Tumblr bot powered by a machine-learning model. This bot would be specifically trained on the content from a particular Tumblr blog or a selected set of blogs, allowing it to mimic the style, tone, and thematic essence of the original posts.](https://github.com/fourteevee/4tv-tumblrbot)

This fork is largely a rewrite of the source code with similarities in its structure and process.

`tumblrbot` is a *text-based user interface* (TUI) designed to make training LLMs, generating posts, and uploading them to a [Tumblr] blog as easy as possible. It is primarily controlled through selection menus that allow for queuing any number of actions. The following actions are available:

- Download posts from configured blogs.
  - Skips redownloading already downloaded posts.
  - Shows overall progress and post previews.
- Create training data to fine-tune a configured model from downloaded posts.
  - Filters out posts that contain more than just text data.
  - Filters out posts that contain configured regular expressions **(disabled by default)**.
  - Only uses the most recent posts from each blog **(disabled by default)**.
    - The number of posts per blog is configurable.
  - Adds configured training data to the data set **(disabled by default)**.
- Filter out any training data flagged by the [OpenAI Moderation API].
- Upload training data to [OpenAI] and begin the fine-tuning process.
  - Resumes monitoring any unfinished fine-tuning processes when restarted.
  - Deletes the uploaded training data if fine-tuning does not succeed **(requires confirmation)**.
  - Stores the output model automatically when fine-tuning is completed successfully.
- Generate and upload posts to a configured blog using a configured fine-tuned model.
  - Creates tags by extracting keywords using the base model with configurable settings.
  - Uploads generated posts as drafts.
  - Reblogs generated posts from configured blogs.
  - Shows overall progress and post previews.
- Delete data saved by `tumblrbot`.
- Reset settings and/or tokens.

In addition, `tumblrbot` will:

- Prompt the user to set necessary settings and authentication tokens if they are ever missing or corrupt.
- Lead the user through authenticating with [Tumblr] [OAuth] and automatically save authentication data.
- Provide cost estimates for fine-tuning a configured model using the currently generated training data.
- Automatically keep the [config] file up-to-date and recreates it if missing (without overriding user settings).

**Known Issues:**

- Fine-tuning can fail after the validation phase due to the training data not passing [OpenAI] moderation checks. There are a few workarounds for this that can also be tried together:
  - You can retry with the same training data. This has reportedly worked before.
  - You can submit the training data to the [OpenAI] moderation API. This has worked consistently for our dataset, but others have reported it not being thorough enough.
  - You can use regular expressions to filter out training data. This is more of a brute-force solution, but it can work if the other solutions do not.
  - You can try limiting your dataset by configuring fewer blogs to download from or limiting the number of posts taken from each one.
  - If all else fails, you can manually remove data from the training data file until it passes. It is unfortunately not a definitive resource, but it can help to read about what the [OpenAI moderation API flags][Flags].
- Post counts can be incorrect when downloading posts. Our tests suggest this is a [Tumblr] API problem that is giving inaccurate numbers, so treat them as estimates.

**To-Do:**

- Allow limiting the newest posts from each blog with a configurable date.
- Change instances of "fine-tuning" to "training" (maybe).

**Please submit an issue or contact us for features you want added/reimplemented.**

---

## Obtaining Tokens

### OpenAI

An API token can be created here: [OpenAI Tokens]

   1. Leave everything at the defaults and set `Project` to `Default Project`.
   1. Press `Create secret key`.
   1. Press `Copy` to copy the API token to your clipboard.

### Tumblr

API tokens can be created here: [Tumblr Tokens]

   1. Press `+ Register Application`.
   1. Enter anything for `Application Name` and `Application Description`.
   1. Enter any URL for `Application Website` and `Default callback URL`, like `https://example.com`.
   1. Enter any email address for `Administrative contact email`. It probably doesn't need to be one you have access to.
   1. Press the checkbox next to `I'm not a robot` and complete the CAPTCHA.
   1. Press `Register`.
   1. You now have access to your `consumer key` next to `Oauth Consumer Key`.
   1. Press `Show secret key` to see your `Consumer Secret`.

When running this program the first time, you will be prompted to enter all of these tokens. If something goes wrong during this process, you can always reset them through the reset menu or by manually editing the tokens file.

After inputting the [Tumblr] tokens, you will be given a URL that you need to open in your browser. Press `Allow`, then copy and paste the URL of the page you are redirected to into the console.

*Empty space is stripped automatically from all values entered into the console.*

## Configuration

All config options can be found in `config.toml` after running the program once. This will be kept up-to-date if there are changes to the config's format in a future update. This also means it may be worthwhile to double-check the config file after an update. Any changes to the config should be in the changelog for a given version.

All file options can include non-existent directories in the path. Any directories that are missing will be created when the program is run.

All config options that involve *blog identifiers* expect any version of a blog URL, which is explained in more detail in the [Tumblr API documentation on blog identifiers].

A valid post:

- Contains any content (filters out glitched empty posts).
- Only has text (filters out posts that have images, polls, videos, etc.).
- Is not an answer to an ask.
- Is not a reblog of another post.
- Is not a submitted post.

### Specific Options

- `custom_prompts_file` This file should follow the following file format:

   ```json
   {"user message 1": "assistant response 1"}
   {"user message 1": "assistant response 1"}
   {"user message 2": "assistant response 2", "user message 3": "assistant response 3"}
   ```

   To be specific, it should follow the [JSON Lines] file format with one collection of name/value pairs (a dictionary) per line. You can validate your file using the [JSON Lines Validator].

- **`post_limit`** - At most, this many valid posts will be included in the training data. This effectively is a filter to select the `N` most recent posts from each blog. `0` will use every available valid post. The actual number of posts per blog included in the training data may be less if there are fewer valid posts than this value.
- **`moderation_batch_size`** - This controls the batch size when submitting posts to the OpenAI moderation. There is no limit, but higher numbers will cause you to be rate-limited more, which can overall be slower. Low numbers reduce rate-limiting, but can sometimes take longer due to needing more requests. The best value will depend on your computer, internet connection, and any number of factors on OpenAI's side. The default value is just what worked decently well for our device.
- **`filtered_words`** - During training data generation, any posts with these configured words will be removed. Word boundaries are not checked by default, so “the” will also filter out posts with “them” or “thematic”. This setting supports regular expressions, so you can explicitly look for word boundaries by surrounding an entry with “\\\b”, i.e., “\\\bthe\\\b”. Regular expressions have to be escaped like so due to how JSON data is read in. If you are familiar with regular expressions, it could be useful for you to know that every entry is joined with a “|” which is then used to search the post content for any matches. If you are not familiar with regular expressions, you just need to know to *escape* certain characters (like periods and asterisks). Escaping, like the example above, requires *three* backslashes to be added before the character. To learn more about regular expressions, and test what you have entered, try out [regex101]. Make sure to select `Python` under `Flavor` on the left of the page.
- **`developer_message`** - This message is used for fine-tuning the AI as well as generating prompts. If you change this, you will need to run the fine-tuning again with the new value before generating posts.
- **`user_message`** - This setting is works in the same way as `developer_message`.
- **`expected_epochs`** - The default value here is the default number of epochs for `base_model`. You may have to change this value if you change `base_model`. After running fine-tuning once, you will see the number of epochs used in the [fine-tuning portal] under *Hyperparameters*. This value will also be updated automatically if you run fine-tuning through `tumblrbot`.
- **`token_price`** - The default value here is the default token price for `base_model`. You can find the up-to-date value in [OpenAI Pricing], in the *Training* column. This is unlikely to change frequently.
- **`job_id`** - If there is any value here, this program will resume monitoring the corresponding fine-tuning job, instead of starting a new one. This gets set when starting the fine-tuning and is cleared when it is completed. You can read more in the [Manual Fine-Tuning] section.
- **`base_model`** - This value is used to estimate fine-tuning costs. It is also the base model that will be fine-tuned and used to generate tags. You can find a list of options in the [fine-tuning portal] by pressing `+ Create` and opening the drop-down list for `Base Model`. Be sure to update `token_price` if you change this value.
- **`fine_tuned_model`** - Set automatically after monitoring fine-tuning if the job has succeeded. You can read more in the [Manual Fine-Tuning] section.
- **`tags_chance`** - This should be between 0 and 1. Setting it to 0 corresponds to a 0% chance (never) to add tags to a post. 1 corresponds to a 100% chance (always) to add tags to a post. Adding tags incurs a very small token cost.
- **`reblog_blog_identifiers`** - Whenever a reblog is attempted, a random blog from this list will be chosen to be reblogged from. If a blog in this list is invalid, an error will occur while generating posts if it is selected.
- **`reblog_chance`** - This setting works the same way as `tags_chance`.
- **`reblog_user_message`** - This setting is a [format string]. The only argument it is formatted with is the content of the post being reblogged. In simple terms, the `{}` will be replaced with said content. Alternatively, you can leave out the `{}` so that the reblogged post is appended to the end.
  - *Note: The bot is only given the latest message in a reblog chain due to the required complexity and added costs of including the entire chain.*

## Manual Fine-Tuning

You can manually upload the training data file to [OpenAI] and start the fine-tuning here: [fine-tuning portal].

1. Press `+ Create`.
1. Select the desired `Base Model` from the dropdown. This should ideally match the model set in the [config].
1. Upload the generated training data file to the section under `Training data`. You can find the path to this file in the [config].
1. Press `Create`.
1. (Optional) Copy the value next to `Job ID` and paste it into the [config] under `job_id`. You can then run the program and monitor its progress as usual.
1. If you do not do the above, you will have to copy the value next to `Output model` once the job is complete, and paste it into the [config] under `fine_tuned_model`.
