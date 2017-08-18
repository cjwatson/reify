import io
import os
import textwrap

import pytest
import contemplate


def test_parse_envfile():
    envfile = io.StringIO(textwrap.dedent("""
        X=x
        # line comment
        Y=y$X  # envfile substitution
        Z=z$Z  # env substitution
        # blank line

    """))
    env = {'Z': 'z'}
    contemplate.parse_envfile(env, envfile)
    assert env == {
        'X': 'x',
        'Y': 'yx',
        'Z': 'zz',
    }


def test_parse_yamlfile():
    assert contemplate.parse_yamlfile(io.StringIO("")) == {}
    assert contemplate.parse_yamlfile(io.StringIO("{}")) == {}
    assert contemplate.parse_yamlfile(io.StringIO("[]")) == {}

    non_dict = io.StringIO("[1]")
    non_dict.name = 'test'
    with pytest.raises(Exception):
        contemplate.parse_yamlfile(non_dict)

    d = contemplate.parse_yamlfile(io.StringIO(textwrap.dedent("""
        foo:
            bar:
                - 1
                - 2
    """)))
    assert d == {'foo': {'bar': [1, 2]}}


def test_atomic_write(tmpdir):
    path = str(tmpdir.join('file'))
    contemplate.atomic_write(path, 'hi')
    assert open(path).read() == 'hi'
    assert not os.path.exists(path + '.contemplate.tmp')


def test_atomic_write_rename_fails(tmpdir, monkeypatch):

    class TestException(Exception):
        pass

    def rename(x, y):
        raise TestException()

    monkeypatch.setattr(os, 'rename', rename)
    path = str(tmpdir.join('file'))
    with open(path, 'w') as f:
        f.write('other')
    with pytest.raises(TestException):
        contemplate.atomic_write(path, 'hi')
    assert not os.path.exists(path + '.contemplate.tmp')
    assert open(path).read() == 'other'


TEMPLATE = "'{{ test }}' '{{ env['TEST'] }}'"


def test_render_none():
    output = contemplate.render(TEMPLATE, {}, None, {})
    assert output == "'' ''\n"


def test_render_simple():
    output = contemplate.render(TEMPLATE, {'test': 'ctx'}, None, {})
    assert output == "'ctx' ''\n"


def test_render_envvar():
    output = contemplate.render(TEMPLATE, {}, None, {'TEST': 'env'})
    assert output == "'' 'env'\n"


def test_render_envfile():
    output = contemplate.render(TEMPLATE, {}, io.StringIO('TEST=envfile'), {})
    assert output == "'' 'envfile'\n"


def test_render_envfile_overrides_env():
    output = contemplate.render(
        TEMPLATE, {}, io.StringIO('TEST=envfile'), {'TEST': 'env'})
    assert output == "'' 'envfile'\n"


def test_render_ctx_overrides_envfile():
    output = contemplate.render(
        TEMPLATE, {'env': {'TEST': 'ctx'}}, io.StringIO('TEST=envfile'), {})
    assert output == "'' 'ctx'\n"