# encoding:utf-8
""" iron.nvim (Interactive Repls Over Neovim).

`iron` is a plugin that allows better interactions with interactive repls
using neovim's job-control and terminal.

Currently it keeps track of a single repl instance per filetype.
"""
import neovim
from copy import deepcopy
from iron.repls import available_repls


@neovim.plugin
class Iron(object):

    def __init__(self, nvim):
        self.__nvim = nvim
        self.__repl = {}
        self.__functions = {}
        self.__eval_mode = False

    def get_repl_template(self, ft):
        repls = list(filter(
            lambda k: ft == k['language'],
            available_repls))
        return len(repls) and repls[0] or {}

    def open_repl_for(self, ft):
        self.__nvim.command('spl | wincmd j | enew')
        repl_id = self.__nvim.call(
            'termopen',
            self.__repl[ft]['command']
        )

        # TODO Make optional nvimux integration detached
        self.__nvim.current.buffer.vars['nvimux_buf_orientation'] = (
            "botright split"
        )

        for k, c in self.__repl[ft].get('mappings', []):
            self.__nvim.command(
                'nnoremap {} :call IronSpecialSend("{}")<CR>'.format(k, k)
            )
            self.__functions[k] = c

        self.__repl[ft]['repl_id'] = repl_id

        return repl_id

    @neovim.function("IronSpecialSend")
    def mapping_send(self, args):
        self.__functions[args[0]](self.__nvim)

    @neovim.command("IronRepl")
    def get_repl(self):
        ft = self.__nvim.current.buffer.options["ft"]

        repl_type = self.__repl[ft] = self.get_repl_template(ft)

        if not repl_type:
            self.__nvim.command("echoerr 'No repl found for {}'".format(ft))

        else:
            repl_id = self.open_repl_for(ft)
            repl_buffer_id = self.__nvim.current.buffer.number
            self.__nvim.vars["iron_current_repl_term"] = repl_buffer_id
            self.__nvim.vars["iron_current_repl"] = repl_buffer_id

    @neovim.function("IronSendToRepl")
    def send_to_repl(self, args):
        ft = (
            args[1]
            if len(args) > 1 else
            self.__nvim.current.buffer.options['ft']
        )

        repl = self.__repl[ft] if ft in self.__repl else None

        if not repl:
            return

        if args[0] == 'line':
            self.__nvim.command("""normal! '[V']"sy""")
        else:
            self.__nvim.command("""normal! `[v`]"sy""")

        data = self.__nvim.funcs.getreg('s')

        multiline = 'multinine' in repl

        if multiline and any(map(
                lambda k: k.isspace(), data.split('\n'))):
            (pre, post) = repl['multiline']
            data = "{}\n{}\n{}".format(pre, data, post)

        self.__nvim.call('jobsend', repl['repl_id'], data)
