#!/bin/bash

BOTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd )"
source "$BOTDIR/start_bot.sh"

if test -d "$CACHE_DIR"; then
	echo "###########################"
	echo "# SteamDealBot Statistics #"
	echo "###########################"
	echo
	echo "Telegram api key: $STEAM_TELEGRAM_API_KEY"
	echo "IsThereAnyDeal api key: $ISTHEREANYDEAL_API_KEY"
	echo "Automatic updates time: $STEAM_UPDATES_HOUR:$STEAM_UPDATES_MINUTE"
	echo

	pushd "$CACHE_DIR" > /dev/null
		echo "Active users:"
		count=0
		for u in tids/*; do
			if test -f "$u"; then
				STR="$(jq -c "[(.username), (.telegram_id), (.cache | length)]" "$u" | sed -e 's/\[/Steam username: /' -e 's/,/, Telegram id: /' -e 's/,\([0-9]\+\)\]$/, cache size: \1/' 2> /dev/null)"
				if test -n "$STR"; then
					echo -e "\t$STR"
					count=$((count+1))
				fi
			fi
		done
		echo
		echo "Total users: $count"
		echo
		echo "Cached Humbe bundles:"
		echo -e "$(jq -c ".cache[].name" bundles_cache | tr -d '"' | sed -e 's/^/\t/')"
		echo
	popd > /dev/null
else
	echo "missing cache dire, is bot running?"
fi
