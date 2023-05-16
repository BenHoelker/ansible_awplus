import subprocess
import os
import ast
import json
import re

pb_dir = os.path.dirname(__file__)

test_configs = {}


def get_config():
    # get the config from the file
    file = open("test_configs/test_banner_configs.json")
    data = json.load(file)
    file.close()
    return data


def setup():
    global test_configs
    test_configs = get_config()


setup()

variables = test_configs.get('variables')
tests = {
    'r_1': ["no banner motd"],
    'r_2': [f"banner exec {variables.get('text_2')}"],
    'r_3': [f"banner exec {variables.get('text_4')}", f"banner motd {variables.get('text_5')}"],
    'r_4': [],
    'r_5': [f"banner exec {variables.get('text_1')}", "no banner motd"],
    'm_1': [],
    'm_2': [f"banner exec {variables.get('text_6')}"],
    'm_3': [f"banner motd {variables.get('text_6')}"],
    'm_4': [],
    'm_5': [],
    'm_6': [],
    'd_1': [],
    'd_2': ["no banner motd"],
    'd_3': [],
    'd_4': ["no banner motd"],
}


def run_playbook(playbook, tag, debug=False):
    if tag != 'test_init':
        result = subprocess.run(['ansible-playbook', '-v', f'-t {tag}', f'{pb_dir}/{playbook}'], stdout=subprocess.PIPE)
    else:
        initial_config = test_configs.get("required_configs").get("test_init")[0]
        result = subprocess.run(["ansible", "aw1", "-m", "awplus_banner", "-a",
                                 f"config='banner={initial_config.get('banner')} text={initial_config.get('text')}' state=replaced"], stdout=subprocess.PIPE)
    if debug:
        print(result.stdout.decode('utf-8'))
    return result.stdout.decode('utf-8')


def parse_output(op, tag='test_init'):
    looking = True
    host = ''
    pop = ""
    for outl in op.splitlines():
        ls = outl.strip()
        if looking:
            if ls.startswith(('ok:', 'changed:', 'fatal:')):
                pop = ""
                looking = False
        else:
            if ls.startswith(('ok:', 'changed:', 'fatal:')):
                pop += ls
                if outl.rstrip() == '}':
                    break

    host_match = re.search(r'(changed|ok|fatal): \[(\S+)\]', pop)
    if host_match:
        host = host_match.group(2)

    pop = pop.replace("false", "False")
    pop = pop.replace("true", "True")
    pop = pop.replace("null", "None")
    pop = pop.replace(f'changed: [{host}] => ', '')
    pop = pop.replace(f'ok: [{host}] => ', '')
    pop = pop.replace(f'fatal: [{host}]: FAILED! => ', '')

    try:
        pop = ast.literal_eval(pop)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return [], []

    if pop.get('changed') is True:
        return pop.get('commands'), pop.get('after') if pop.get('after') != {} else []
    elif pop.get('msg'):
        return pop.get('commands') if pop.get('commands') else [], pop.get('msg')
    else:
        return pop.get('commands'), pop.get('before') if pop.get('before') != {} else []


def check_list(list1, list2, debug=False):
    if debug:
        print(list1, list2)
    return sorted(list1) == sorted(list2)


def check_config(parsed_config, required_config, debug=False):
    result = (parsed_config == required_config)
    if debug:
        print(f"configs:\nrequired_config: '{required_config}'\nparsed_config: '{parsed_config}'")
    return result


def run_a_test(test_name, debug=False):
    global test_configs

    if test_name not in tests:
        return True

    # test_init
    op = run_playbook('test_awplus_banner.yml', 'test_init')
    pop, after = parse_output(op)

    # test
    op = run_playbook('test_awplus_banner.yml', test_name)
    pop, after = parse_output(op, test_name)

    # check if the test passes
    conf_after = test_configs.get('required_configs').get(test_name)
    check_conf = check_config(after, conf_after if conf_after is not None else [], debug=debug)
    check_cmd = check_list(pop, tests[test_name], debug=debug)
    return check_conf and check_cmd


def test_replace_empty_config_1__1():
    assert run_a_test('r_1')


def test_add_new_banner_with_replaced__2():
    assert run_a_test('r_2')


def test_replace_existing_config__3():
    assert run_a_test('r_3')


def test_replace_idempotent_config__4():
    assert run_a_test('r_4')


def test_replace_banner_type__5():
    assert run_a_test('r_5')


def test_merge_empty_config__6():
    assert run_a_test('m_1')


def test_merge_new_config__7():
    assert run_a_test('m_2')


def test_merge_existing_config__8():
    assert run_a_test('m_3')


def test_merge_insufficient_config_1__9():
    assert run_a_test('m_4')


def test_merge_insufficient_config_2__10():
    assert run_a_test('m_5')


def test_merge_idempotent_config__11():
    assert run_a_test('m_6')


def test_delete_empty_config__12():
    assert run_a_test('d_1')


def test_delete_config_using_banner_type__13():
    assert run_a_test('d_2')


def test_delete_using_text__14():
    assert run_a_test('d_3')


def test_delete_using_same_config__15():
    assert run_a_test('d_4')
