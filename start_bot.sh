#!/bin/bash

CONFIG_DIR="$HOME/.config/steam_dealbot"
CONFIG_FILE="$CONFIG_DIR/steam_dealbot_config.sh"
TEMPLATE_FILE="$(dirname "${BASH_SOURCE[0]}")/template_config.sh"
EXCLUDES_FILE="$CONFIG_DIR/excludes"
DB_FILE="$CONFIG_DIR/latest_deals"

if test ! -d "$CONFIG_DIR" -o ! -x "$CONFIG_FILE"; then
	if test ! -d "$CONFIG_DIR"; then
		mkdir -p "$CONFIG_DIR"
	fi
	if test ! -f "$CONFIG_FILE"; then
		cp "$TEMPLATE_FILE" "$CONFIG_FILE"
	fi
	if test ! -x "$CONFIG_FILE"; then
		chmod +x "$CONFIG_FILE"
	fi
fi

if test -z "$EDITOR"; then
	EDITOR='vi'
fi

if test "$1" = "-e"; then
	$EDITOR $CONFIG_FILE
elif test -n "$1"; then
	echo "$(basename "${BASH_SOURCE[0]}") - start steam deal list bot"
	echo
	echo "Usage:"
	echo -e "\t$(basename "${BASH_SOURCE[0]}") [OPTIONS]"
	echo 
	echo "OPTIONS:"
	echo -e "\t-e : edit config file before launch"
	echo -e "\t-h : show this help"
	echo
	if test "$1" != "-h" -a "$1" != "--help"; then
		echo "unknown option \"$1\""
		exit 1
	fi
	exit 0
fi

UNSETVARS="$(egrep '=["]?[X]+["]?$' "$CONFIG_FILE")"
while test -n "$UNSETVARS"; do
	echo "you need to set all variables in config file $(readlink -f "$CONFIG_FILE")"
	echo "unset variables:"
	echo "$UNSETVARS"
	echo
	echo "do you want to edit file now (using default editor '$EDITOR')? [Y/n]"
	read ANSWER
	if test -z "$ANSWER" -o "$ANSWER" = 'Y' -o "$ANSWER" = 'y'; then
		$EDITOR "$CONFIG_FILE"
	else
		exit 0
	fi
	UNSETVARS="$(egrep '=["]?[X]+["]?$' "$CONFIG_FILE")"
done

source "$CONFIG_FILE"
#touch "$EXCLUDES_FILE" "$DB_FILE"

python3 "$(dirname "${BASH_SOURCE[0]}")"/steam_dealbot.py "$EXCLUDES_FILE" "$DB_FILE"
