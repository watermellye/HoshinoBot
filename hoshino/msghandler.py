from nonebot.command import SwitchException

from hoshino import CanceledException, message_preprocessor, trigger
from hoshino.typing import CQEvent


@message_preprocessor
async def handle_message(bot, event: CQEvent, _):
    if len(event.message.extract_plain_text()) > 512:
        raise CanceledException('ignore too long messages')

    if event.detail_type != 'group':
        pass # return

    for t in trigger.chain:
        for service_func in t.find_handler(event):
            if service_func.only_to_me and not event['to_me']:
                continue  # not to me, ignore.

            if not service_func.sv._check_all(event):
                continue  # permission denied.

            service_func.sv.logger.info(f'Message {event.message_id} triggered {service_func.__name__}.')
            try:
                await service_func.func(bot, event)
            except SwitchException:     # the func says: continue to trigger another function.
                continue
            except CanceledException:   # the func says: stop triggering.
                raise
            except Exception as e:      # other general errors.
                service_func.sv.logger.error(f'{type(e)} occured when {service_func.__name__} handling message {event.message_id}.')
                service_func.sv.logger.exception(e)
            # the func completed successfully, stop triggering. (1 message for 1 function at most.)
            raise CanceledException('Handled by Hoshino')
            # exception raised, no need for break
