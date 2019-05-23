#!/usr/bin/env python3

from argparse import Action, ArgumentParser
from typing import Callable, Any, Union, List
from sys import stderr


def promptor(
    argument_name: str,
    type_converter: Callable[[str], Any],
    use_list: bool,
    num_required_args: int
) -> Union[List[Any], Any]:
    """

    :param argument_name: The name of the argument whose value to be input.
    :param type_converter: A converter
    :param use_list:
    :param num_required_args:
    :return:
    """

    full_value = None
    while not full_value:
        inputted_value = None
        while not inputted_value:
            inputted_value = input(f'{argument_name}: ').strip()
            if use_list and len(inputted_value.split(', ')) != num_required_args:
                print(f'Incorrect number of arguments provided. Need {num_required_args}. Try again.', file=stderr)
                inputted_value = None
            if not inputted_value and num_required_args == 0:
                return ''

        try:
            if use_list:
                full_value = [
                    type_converter(inputted_value_element)
                    for inputted_value_element in inputted_value.split(', ')
                ]
            else:
                full_value = type_converter(inputted_value)
        except:
            print(f'Could not convert the inputted value to its specified type. Try again.', file=stderr)
            continue

    return full_value


class PromptArgumentParserAction(Action):
    def __init__(self, **kwargs):

        self.provided_restored = False

        # Save the user-provided `add_argument` arguments in order to have `print_usage` and `print_help` print the
        # their messages in the correct format.
        self._required = kwargs.get('required')
        self._nargs = kwargs.get('nargs')
        self._type = kwargs.get('type')
        self._default = kwargs.get('default')

        if self._nargs in {'*', '?'}:
            num_required_args = 0
        elif self._nargs == '+':
            num_required_args = 1
        else:
            num_required_args = int(self._nargs or '1')

        kwargs['nargs'] = '*' if num_required_args > 1 else '?'
        kwargs['type'] = lambda value: value if value else promptor(
            argument_name=kwargs['dest'],
            type_converter=kwargs.get('type', str),
            use_list=self._nargs != '?' and self._nargs in {'*', '+'} or int(self._nargs or '1') > 1,
            num_required_args=num_required_args
        )
        kwargs['default'] = ''
        kwargs['required'] = False

        # Save the crafted `add_argument` arguments in case `print_usage` or `print_help` is called in between this
        # action registration and `parse_args`.
        self.__required = kwargs['required']
        self.__nargs = kwargs['nargs']
        self.__type = kwargs['type']
        self.__default = kwargs['default']

        super().__init__(**kwargs)

    def restore_provided(self) -> None:
        """
        Restort the user-provided `add_argument` arguments.

        The purpose of this method is to have `parse_args` use the correct, user-provided arguments when producing the
        `print_help` and `print_usage` texts.
        :return:
        """
        self.required = self._required
        self.nargs = self._nargs
        self.type = self._type
        self.default = self._default

    def restore_crafted(self) -> None:
        """
        Restore the crafted `add_argument` arguments.

        The purpose of this method is to have `parse_args` use the correct, crafted arguments even if `print_help` or
        `print_usage` is called in between this `PromptArgumentParserAction` is registered and `parse_args` is called.
        :return:
        """

        self.required = self.__required
        self.nargs = self.__nargs
        self.type = self.__type
        self.default = self.__default

    def __call__(self, parser, namespace, result_value, option_string=None):
        self.restore_provided()
        setattr(namespace, self.dest, result_value)


class PromptArgumentParser(ArgumentParser):

    def add_argument(self, *args, **kwargs):
        if (kwargs.get('required') or not next(iter(args)).startswith('-')) and 'default' not in kwargs:
            kwargs['action'] = PromptArgumentParserAction
        super().add_argument(*args, **kwargs)

    def print_help(self, file=None):
        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action._provided_restored:
                action.restore_provided()

        super().print_help(file)

        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action._provided_restored:
                action.restore_crafted()

    def print_usage(self, file=None):
        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action._provided_restored:
                action.restore_provided()

        super().print_usage(file)

        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action._provided_restored:
                action.restore_crafted()
