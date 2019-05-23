#!/usr/bin/env python3

from argparse import Action, ArgumentParser
from typing import Callable, Any, Union, List
from sys import stderr


def promptor(
    parameter_name: str,
    type_converter: Callable[[str], Any],
    use_list: bool,
    num_required_args: int
) -> Union[List[Any], Any]:
    """
    Prompt for input for a parameter.

    :param parameter_name: The name of the parameter whose value to be input.
    :param type_converter: A type converter for the parameter to be applied to the inputted values.
    :param use_list: Whether the value resulting from the input should be a a list.
    :param num_required_args: The number of arguments the parameter requires, and one must input.
    :return: A single type converted inputted value or a list of inputted type converted values.
    """

    full_value = None
    while not full_value:
        inputted_value = None
        while not inputted_value:
            inputted_value = input(f'{parameter_name}: ').strip()
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
        self._argument_name = next(iter(kwargs['option_strings'])) if kwargs.get('option_strings') else kwargs['dest']

        # Save the user-provided `add_argument` arguments in order to have `print_usage` and `print_help` print their
        # messages in the correct format.
        self._required = kwargs.get('required')
        self._nargs = kwargs.get('nargs')
        self._type = kwargs.get('type')
        self._default = kwargs.get('default')

        # Let the prompter know how many arguments are required for this parameter. Also, because `nargs` is overwritten
        # we must also check that the number of user-provided arguments is correct.
        if self._nargs in {'*', '?'}:
            self._num_required_args = 0
        elif self._nargs == '+':
            self._num_required_args = 1
        else:
            self._num_required_args = int(self._nargs or '1')

        # Specify whether the parsed value will result in a list. Using "*" and "?" assures providing a value for the
        # parameter is optional, so that the providing can be handled by the prompt.
        kwargs['nargs'] = '*' if self._num_required_args > 1 else '?'
        # In case an argument value is provided via the terminal, use it. Otherwise, prompt.
        kwargs['type'] = lambda value: value if value else promptor(
            parameter_name=kwargs['dest'],
            type_converter=kwargs.get('type', str),
            use_list=self._nargs != '?' and self._nargs in {'*', '+'} or int(self._nargs or '1') > 1,
            num_required_args=self._num_required_args
        )
        # From the Python documentation (https://docs.python.org/3/library/argparse.html#default):
        # """
        # If the default value is a string, the parser parses the value as if it were a command-line argument. In
        # particular, the parser applies any type conversion argument [...] Otherwise, the parser uses the value as is.
        # """
        kwargs['default'] = ''
        # To to have required arguments that have options flags be handled by a prompt, and not raise an error, they
        # must `required` needs to be set to `False`.
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

        if self._num_required_args > 1 and len(result_value) != self._num_required_args:
            parser.print_usage()
            print(f'{parser.prog}: error: argument {self._argument_name} expects {self._num_required_args} arguments')
            exit(1)

        self.restore_provided()
        setattr(namespace, self.dest, result_value)


class PromptArgumentParser(ArgumentParser):

    def add_argument(self, *args, **kwargs):
        if (kwargs.get('required') or not next(iter(args)).startswith('-')) and 'default' not in kwargs:
            kwargs['action'] = PromptArgumentParserAction
        super().add_argument(*args, **kwargs)

    def print_help(self, file=None):
        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action.provided_restored:
                action.restore_provided()

        super().print_help(file)

        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action.provided_restored:
                action.restore_crafted()

    def print_usage(self, file=None):
        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action.provided_restored:
                action.restore_provided()

        super().print_usage(file)

        for action in self._actions:
            if isinstance(action, PromptArgumentParserAction) and not action.provided_restored:
                action.restore_crafted()
