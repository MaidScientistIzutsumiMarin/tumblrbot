[OpenAI]: https://pypi.org/project/openai
[Python]: https://python.org/download
[Rich]: https://pypi.org/project/rich

[gpt-4.1-nano-2025-04-14]: https://platform.openai.com/docs/models/gpt-4.1-nano
[Moderation API]: https://platform.openai.com/docs/api-reference/moderations
[New Post Format]: https://tumblr.com/docs/npf
[OAuth 2.0]: https://www.tumblr.com/docs/en/api/v2#oauth2-authorization
[pip]: https://pypi.org

[Download]: tumblrbot/flow/download.py
[Examples]: tumblrbot/flow/examples.py
[Fine-Tune]: tumblrbot/flow/fine_tune.py
[Generate]: tumblrbot/flow/generate.py
[Settings]: tumblrbot/utils/settings.py
[Main]: __main__.py
[README.md]: README.md

# tumblrbot
[![PyPI - Version](https://img.shields.io/pypi/v/tumblrbot)](https://python.org/pypi/tumblrbot)

Description of original project:
> 4tv-tumblrbot was a collaborative project I embarked on with my close friend Dima, who goes by @smoqueen on Tumblr. The aim of this endeavor was straightforward yet silly: to develop a Tumblr bot powered by a machine-learning model. This bot would be specifically trained on the content from a particular Tumblr blog or a selected set of blogs, allowing it to mimic the style, tone, and thematic essence of the original posts.

This fork is largely a rewrite of the source code with similarities in its structure and process:
- Updates:
   - Updated to [OAuth 2.0].
   - Updated to the [New Post Format].
   - Updated to the latest version of [OpenAI].
   - Updated the [base model version][Settings] to [gpt-4.1-nano-2025-04-14].
- Removed features:
   - [Generation][Generate]:
      - Removed clearing drafts behavior.
   - [Training][Examples]:
      - Removed exports that had HTML or reblogs.
      - Removed special word-replacement behavior.
      - Removed filtering by year.
   - Removed setup and related files.
- Changed/Added features:
   - [Generation][Generate]:
      - Added a link to the blog's draft page.
      - Added error checking for uploading drafts.
   - [Training][Examples]:
      - Added the option to [Download] the latest posts from the [specified blogs][Settings].
      - Added the option to remove posts flagged by the [Moderation API].
      - Added the option to automatically [Fine-Tune] the examples on the [specified base model][Settings].
      - Changed to now escape examples automatically.
      - Set encoding for reading post data to `UTF-8` to fix decoding errors.
      - Added newlines between paragraphs.
      - Removed "ALT", submission, ask, and poll text from posts.
      - Improved the estimated token counts and costs.
   - Changed to [Rich] for output.
      - Added progress bars.
      - Added post previews.
      - Added color, formatting, and more information to output.
   - Created a [guided utility][Main] for every step of building your bot blog.
   - Maid scripts wait for user input before the console closes.
   - Added comand-line options to override [Settings] options.
   - Added behavior to regenerate the default [config.toml][Settings] and [env.toml][Settings] if missing.
   - Renamed several files.
   - Renamed several [Settings] options.
   - Changed the value of several [Settings] options.
   - Added full type-checking coverage (fully importable from third-party scripts).

To-Do:
- Add documentation.
- Finish updating [README.md].
- Look into places more-itertools can help.
- Change the differences list to instead just be a list of features.


**Please submit an issue or contact us for features you want to added/reimplemented.**

## Installation
1. Install the latest version of [Python]:
   - Windows: `winget install python3`
   - Linux (apt): `apt install python-pip`
   - Linux (pacman): `pacman install python-pip`
1. Install the [pip] package: `pip install tumblrbot`
   - Alternatively, you can install from this repository: `pip install git+https://github.com/MaidThatPrograms/tumblrbot.git`
   - On Linux, you will have to make a virtual environment.

## Usage
Run `tumblrbot` from anywhere. Run `tumblrbot --help` for command-line options.

## Obtaining Tokens
> WIP

## Configuration
> WIP
