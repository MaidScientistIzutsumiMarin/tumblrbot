pyinstaller.exe `
    --noconfirm `
    --onefile `
    --name tumblrbot `
    --hidden-import tiktoken_ext.openai_public `
    --optimize 2 `
    src\tumblrbot\__main__.py
