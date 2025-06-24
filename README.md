[Beautiful Soup]: https://pypi.org/project/beautifulsoup4
[lxml]: https://pypi.org/project/lxml
[OpenAI]: https://pypi.org/project/openai
[Rich]: https://pypi.org/project/rich
[tumblr-backup]: https://pypi.org/project/tumblr-backup

[gpt-4.1-nano]: https://platform.openai.com/docs/models/gpt-4.1-nano
[pip]: https://pypi.org
[New Post Format]: https://tumblr.com/docs/npf

[json.dump]: https://docs.python.org/3/library/json.html#json.dump
[max output tokens]: https://platform.openai.com/docs/api-reference/responses/create#responses-create-max_output_tokens
[temperature]: https://platform.openai.com/docs/api-reference/responses/create#responses-create-temperature

[.env.toml]: Sample%20.env.toml
[Config]: config.toml
[Generation]: generation.py
[README.md]: README.md
[Training]: training.py

# tumblrbot
Description of original project:
> 4tv-tumblrbot was a collaborative project I embarked on with my close friend Dima, who goes by @smoqueen on Tumblr. The aim of this endeavor was straightforward yet silly: to develop a Tumblr bot powered by a machine-learning model. This bot would be specifically trained on the content from a particular Tumblr blog or a selected set of blogs, allowing it to mimic the style, tone, and thematic essence of the original posts.

This fork is largely a rewrite of the source code with similarities in its structure and process:
- Removed features:
   - [Generation]:
      - Removed command-line options.
      - Removed clearing drafts behavior.
      - Removed the tag limit.
   - [Training]:
      - Removed exports that had HTML or reblogs.
      - Removed special word-replacement behavior.
      - Removed filtering by year.
   - Removed the system message.
   - Removed setup and related files.
- Changed/Added features:
   - [Generation]:
      - Changed to the default [temperature] for tags.
      - Changed to the default [max output tokens].
      - Changed the draft format to HTML.
      - Added a link to the blog's draft page after generation.
      - Added error checking for uploading generated drafts.
   - [Training]:
      - Changed to escaping training data automatically with [json.dump].
      - Changed to [lxml] for [Beautiful Soup].
      - Set encoding for reading post data to `UTF-8` to fix decoding errors.
      - Added spaces between paragraphs in the training data.
      - Removed "ALT" and poll text from the training data.
      - Improved estimated token counts and costs.
      - Added [tumblr-backup] to automatically download post data.
   - Updated to the latest version of [OpenAI].
   - Updated the [model version][Config] to [gpt-4.1-nano].
   - Changed to [Rich] for output.
   - Added full type-checking coverage.
   - Maid scripts wait for user input before the console closes.
   - Added progress bars.
   - Added post previews.
   - Added color, formatting, and more information to output.
   - Renamed several files.
   - Renamed several [Config] options.
   - Changed the value of several [Config] options.

Probable To-Dos:
- Add documentation.
- Create `__main__.py` which will be an entry point for everything, including fine-tuning and downloading posts.
- Add token cost estimate for [Generation].
- Add command line arguments for [Config] options.
- Finish updating [README.md].

Possible To-Dos:
- Create a simple Tumblr API wrapper that supports the [New Post Format].
- Use classes to store settings data instead of global variables.
- Make this an installable [pip] package.
- Add an OpenAI model pricing and max output tokens scraper.
- Add information about the current [OpenAI] budget.
- Generate [Config] if not present.
- Ask for and store user tokens instead of using [.env.toml].
- Add command-line options for [tumblr-backup].


**Please submit an issue or contact us for features you want to added/reimplemented.**

## Preparation with TumblThree

**Download and Install TumblThree:**

- Visit the official [TumblThree GitHub page](https://github.com/TumblThreeApp/TumblThree) and download the latest version of the application.
- Extract the downloaded ZIP file and run the `TumblThree.exe` file to launch the application.

**Add Tumblr Blogs:**

- Copy the URLs of the Tumblr blogs you want to download.
- In TumblThree, enter the blogs into the field marked **Enter URL**, then hit enter.
- The blogs will be added to the list of blogs in the main interface.

**Configure Download Settings:**

- Click on a blog in the list to view its settings on the right panel.
- Choose which content types you want to download, including text posts, answers, and more. 

**Start Downloading:**

- Click the **Download** button (represented by a download icon) to begin downloading the selected blogs.
- The application will download all available posts from the blogs based on your configuration.



## Setup

#### 1. Move Text Post Files to the Data Folder

- Organize your text post files by moving them to the `./data` directory within the project. Ensure that all your post files are stored here for easy access by the software.

#### 2. Rename Text Post Files

- Rename each text post file following the format:

  ```
  blogname_typeofpost.txt
  ```

  For example:

  - If the blog name is "myblog" and the post is a "texts", rename it to `myblog_texts.txt`.

#### 3. Install Python 3.11

- **For Windows:**

  1. Download Python 3.11 from the [official Python website](https://www.python.org/downloads/windows/).
  2. Run the installer and select the checkbox to "Add Python to PATH" during installation.
  3. Complete the installation process by following the prompts.

- **For Linux:**

  1. Open the terminal.

  2. Run the following commands:

     ```bash
     sudo apt update
     sudo apt install python3.11
     ```

#### 4. Install Pip

- **For Windows:**

  1. Open Command Prompt.

  2. Run the following command to install pip:

     ```bash
     python -m ensurepip --upgrade
     ```

- **For Linux:**

  1. Open the terminal.

  2. Run the following command:

     ```bash
     sudo apt install python3-pip
     ```

#### 5. Install Virtualenv

- **For Windows:**

  1. Open Command Prompt.

  2. Run the following command to install `virtualenv`:

     ```bash
     pip install virtualenv
     ```

- **For Linux:**

  1. Open the terminal.

  2. Run the following command:

     ```bash
     sudo pip install virtualenv
     ```

#### 6. Run the Setup Script

- **For Windows:**

  1. Navigate to the project directory in Command Prompt.

  2. Run the following command:

     ```bash
     setup.bat
     ```

- **For Linux:**

  1. Open the terminal and navigate to the project directory.

  2. Run the following command:

     ```bash
     ./setup.sh
     ```

#### 7. Run Python Programs within the Virtual Environment

- **For Windows:**

  1. Activate the virtual environment by running:

     ```bash
     .\venv\Scripts\activate
     ```

  2. Once activated, run any of the Python programs with:

     ```bash
     python {program}.py
     ```

- **For Linux:**

  1. Activate the virtual environment by running:

     ```bash
     source venv/bin/activate
     ```

  2. Once activated, run any of the Python programs with:

     ```bash
     python3 {program}.py
     ```



## Testing

1. **Configure the Settings**: 
   - Open the config file and fill in the required options. 
   - Leave the `model` field blank for now, as it will be completed later after model training is complete.

2. **Prepare Training Data**: 
   - Place your correctly formatted post files into the `./data/` directory.
   - Run the script `create_training_data.py` to generate the necessary training data.

3. **Upload Training Data**: 
   - Once the training files are generated, locate them in the `./output/` folder.
   - Upload these files to OpenAI's fine-tuning web portal.
   - **Ensure you select the most recent version of the `gpt-4o-mini` model** for the fine-tuning process.

4. **Update the Config File**: 
   - After the fine-tuning process is complete, copy the model identifier from OpenAI’s web portal.
   - Paste the model identifier into the `model` field of your config file.

5. **Test the Model**: 
   - Run the script `4tv_tumblrbot.py` to generate posts. These posts will be saved in your Tumblr drafts.
   - Review the output in your drafts. If needed, repeat the process with different blogs or make adjustments to the training data to improve the model.



## Deployment

### Linux Instructions

1. **Place Your Python Script and Virtual Environment**

   - Ensure `4tv_tumblrbot.py` and the virtual environment (`.venv/`) are located in `/home/user/4tv-tumblrbot-1.0/`.

2. **Create a Shell Script to Run the Python Script**

   - Create a shell script named `run_4tv_tumblrbot.sh` in the same directory:

   ```bash
   #!/bin/bash
   cd /home/user/4tv-tumblrbot-1.0/
   source .venv/bin/activate
   python 4tv_tumblrbot.py
   deactivate
   ```

3. **Make the Shell Script Executable**

   - Run the following command to make the shell script executable:

   ```bash
   chmod +x /home/user/4tv-tumblrbot-1.0/run_4tv_tumblrbot.sh
   ```

4. **Schedule the Script Using Cron**

   - Open the cron table:

   ```bash
   crontab -e
   ```

   - Add the following line to schedule the script to run daily at 2 AM:

   ```bash
   0 2 * * * /home/user/4tv-tumblrbot-1.0/run_4tv_tumblrbot.sh >> /home/user/4tv-tumblrbot-1.0/output.log 2>&1
   ```

   - This will log the output to `output.log` in the script's directory.

5. **Verify the Cron Job**

   - List your cron jobs to ensure it was added correctly:

   ```bash
   crontab -l
   ```

### Windows Instructions

1. **Place Your Python Script and Virtual Environment**

   - Ensure `4tv_tumblrbot.py` and the virtual environment (`.venv/`) are located in `C:\Users\user\4tv-tumblrbot-1.0\`.

2. **Create a Batch File to Run the Python Script**

   - Create a batch file named `run_4tv_tumblrbot.bat` in the same directory:

   ```batch
   @echo off
   cd C:\Users\user\4tv-tumblrbot-1.0\
   call .venv\Scripts\activate
   python 4tv_tumblrbot.py
   call .venv\Scripts\deactivate
   ```

3. **Schedule the Script Using Task Scheduler**

   - Open **Task Scheduler** by searching for it in the Start Menu.
   - Click **Create Basic Task** and name your task (e.g., “Run 4tv Tumblrbot Daily”).
   - Set the trigger to "Daily" and select the time (e.g., 2:00 AM).
   - Choose "Start a program" as the action.
   - In the **Program/script** field, enter the path to the batch file (`C:\Users\user\4tv-tumblrbot-1.0\run_4tv_tumblrbot.bat`).
   - Click **Finish** to create the task.

4. **Verify the Task**

   - Check the **Task Scheduler Library** to confirm your task is listed.
   - Optionally, run the task manually to ensure it works by right-clicking the task and selecting **Run**.

### Additional Notes:

- Make sure Python and the virtual environment are properly set up on both systems.
- Adjust paths and timings according to your preferences and system configurations.
- Ensure the script and virtual environment have appropriate permissions and configurations to run correctly.
