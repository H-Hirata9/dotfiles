import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dotenvx_doctor as d


def test_env_is_encrypted_true():
    env = 'DOTENV_PUBLIC_KEY="abc"\nTOKEN="encrypted:BH1S=="\n'
    assert d.env_is_encrypted(env) is True


def test_env_is_encrypted_false_plain():
    env = "TOKEN=plainsecret\n"
    assert d.env_is_encrypted(env) is False


def test_env_is_encrypted_false_no_pubkey():
    env = 'TOKEN="encrypted:xx"\n'
    assert d.env_is_encrypted(env) is False


def test_find_plaintext_keys_detects_plain():
    env = 'DOTENV_PUBLIC_KEY="pk"\nA="encrypted:xx"\nB=plainvalue\nC=\n# comment\n'
    assert d.find_plaintext_keys(env) == ["B"]


def test_find_plaintext_keys_all_encrypted():
    env = 'DOTENV_PUBLIC_KEY="pk"\nA="encrypted:xx"\nB="encrypted:yy"\n'
    assert d.find_plaintext_keys(env) == []


def test_keys_file_has_private():
    assert d.keys_file_has_private('DOTENV_PRIVATE_KEY="deadbeef"\n') is True
    assert d.keys_file_has_private("# no key here\n") is False


def test_py_files_with_load_dotenv():
    texts = {
        "a.py": "from dotenv import load_dotenv\nload_dotenv()\n",
        "b.py": "import os\nx = os.environ['T']\n",
    }
    assert d.py_files_with_load_dotenv(texts) == ["a.py"]


def test_py_files_with_load_dotenv_clean():
    assert d.py_files_with_load_dotenv({"b.py": "import os\n"}) == []
