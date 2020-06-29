# mswar-bot-autopvp
Bot with pvp feature in minesweeper war, side project of mswar-bot.

## Usage
* Register an account on minesweeper war.
* Using a HTTP capturer to catch your account and token.
* Install Python >= 3.7.
* Run `pip install -r requirements.txt`.
* Execute `run.py` with Python.

## Addtional Notice
The program won't run without an valid account, please create the following file by yourself:
* `account_config.py`:
```py
    # Fill in the uid and token below
    uid = 'your-uid-here'
    token = 'your-login-token-here' 
```

The program won't run without a ban list, please create the following file by yourself:
* `ban.py`:
```py
    # create a ban_list: find uid and make a list of them to block out
    ban_list = [
        'xxx',
        'yyy',
        'zzz',
    ]
```
