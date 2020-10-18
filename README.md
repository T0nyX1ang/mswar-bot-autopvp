# mswar-bot-autopvp
Bot with pvp feature in minesweeper war, side project of mswar-bot.

## Usage
* Register an account on minesweeper war.
* Using a HTTP capturer to catch your account and token.
* Install Python >= 3.7.
* Run `pip install -r requirements.txt`.
* Execute `run.py` with Python.

## Addtional Notice
The program won't run without an valid configuration, please create the following file by yourself:
* `account_config.py`:
```py
	# Please set your user configurations here

	host = str
	uid = str
	token = str
	key = str
	salt = str
	version = int
	max_level = float
	min_level = float
	inc_factor = float
	dec_factor = float
	normal_max = int
	vip_max = int
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
