# SCP-079-NOFLOOD - Message-flooding prevention
# Copyright (C) 2019 SCP-079 <https://scp-079.org>
#
# This file is part of SCP-079-NOFLOOD.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import re
from copy import deepcopy

from pyrogram import Client, Filters, Message

from .. import glovar
from ..functions.channel import get_debug_text, share_data
from ..functions.etc import bold, code, delay, get_command_context, get_command_type, get_config_text, get_int, get_now
from ..functions.etc import lang, thread, user_mention
from ..functions.file import save
from ..functions.filters import from_user, is_class_c, test_group
from ..functions.group import delete_message
from ..functions.telegram import get_group_info, send_message, send_report_message

# Enable logging
logger = logging.getLogger(__name__)


@Client.on_message(Filters.incoming & Filters.group & ~test_group & from_user
                   & Filters.command(["config"], glovar.prefix))
def config(client: Client, message: Message) -> bool:
    # Request CONFIG session
    try:
        gid = message.chat.id
        mid = message.message_id
        # Check permission
        if is_class_c(None, message):
            # Check command format
            command_type = get_command_type(message)
            if command_type and re.search(f"^{glovar.sender}$", command_type, re.I):
                now = get_now()
                # Check the config lock
                if now - glovar.configs[gid]["lock"] > 310:
                    # Set lock
                    glovar.configs[gid]["lock"] = now
                    save("configs")
                    # Ask CONFIG generate a config session
                    group_name, group_link = get_group_info(client, message.chat)
                    share_data(
                        client=client,
                        receivers=["CONFIG"],
                        action="config",
                        action_type="ask",
                        data={
                            "project_name": glovar.project_name,
                            "project_link": glovar.project_link,
                            "group_id": gid,
                            "group_name": group_name,
                            "group_link": group_link,
                            "user_id": message.from_user.id,
                            "config": glovar.configs[gid],
                            "default": glovar.default_config
                        }
                    )
                    # Send a report message to debug channel
                    text = get_debug_text(client, message.chat)
                    text += (f"{lang('admin_group')}{lang('colon')}{code(message.from_user.id)}\n"
                             f"{lang('action')}{lang('colon')}{code(lang('config_create'))}\n")
                    thread(send_message, (client, glovar.debug_channel_id, text))

            delay(3, delete_message, [client, gid, mid])
        else:
            thread(delete_message, (client, gid, mid))

        return True
    except Exception as e:
        logger.warning(f"Config error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group & ~test_group & from_user
                   & Filters.command(["config_noflood"], glovar.prefix))
def config_directly(client: Client, message: Message) -> bool:
    # Config the bot directly
    try:
        gid = message.chat.id
        mid = message.message_id
        # Check permission
        if is_class_c(None, message):
            aid = message.from_user.id
            success = True
            reason = lang("config_updated")
            new_config = deepcopy(glovar.configs[gid])
            text = f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"
            # Check command format
            command_type, command_context = get_command_context(message)
            if command_type:
                if command_type == "show":
                    text += f"{lang('action')}{lang('colon')}{code(lang('config_show'))}\n"
                    text += get_config_text(new_config)
                    thread(send_report_message, (30, client, gid, text))
                    thread(delete_message, (client, gid, mid))
                    return True

                now = get_now()
                # Check the config lock
                if now - new_config["lock"] > 310:
                    if command_type == "default":
                        if not new_config.get("default"):
                            new_config = deepcopy(glovar.default_config)
                    else:
                        if command_context:
                            if command_type in {"delete", "purge"}:
                                if command_context == "off":
                                    new_config[command_type] = False
                                elif command_context == "on":
                                    new_config[command_type] = True
                                else:
                                    success = False
                                    reason = lang("command_para")
                            elif command_type == "limit":
                                limit = get_int(command_context)
                                if 2 <= limit <= 20:
                                    new_config["limit"] = limit
                                else:
                                    success = False
                                    reason = lang("command_para")
                            elif command_type == "time":
                                time = get_int(command_context)
                                if 5 <= time <= 60 and time in set(range(5, 65, 5)):
                                    new_config["time"] = time
                                else:
                                    success = False
                                    reason = lang("command_para")
                            else:
                                success = False
                                reason = lang("command_type")
                        else:
                            success = False
                            reason = lang("command_lack")

                        if success:
                            new_config["default"] = False
                else:
                    success = False
                    reason = lang("config_locked")
            else:
                success = False
                reason = lang("command_usage")

            if success and new_config != glovar.configs[gid]:
                glovar.configs[gid] = new_config
                save("configs")

            text += (f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                     f"{lang('status')}{lang('colon')}{code(reason)}\n")
            thread(send_report_message, ((lambda x: 10 if x else 5)(success), client, gid, text))

        thread(delete_message, (client, gid, mid))

        return True
    except Exception as e:
        logger.warning(f"Config directly error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group & test_group & from_user
                   & Filters.command(["version"], glovar.prefix))
def version(client: Client, message: Message) -> bool:
    # Check the program's version
    try:
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id
        text = (f"{lang('admin')}{lang('colon')}{user_mention(aid)}\n\n"
                f"{lang('version')}{lang('colon')}{bold(glovar.version)}\n")
        thread(send_message, (client, cid, text, mid))

        return True
    except Exception as e:
        logger.warning(f"Version error: {e}", exc_info=True)

    return False
