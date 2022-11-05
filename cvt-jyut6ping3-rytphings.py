import argparse
import os, os.path as osp
import re
import time


parser = argparse.ArgumentParser()
parser.add_argument('--jyut6ping3-dir', type=str,
    default="rime-cantonese")
parser.add_argument('--dict-files', type=str, nargs='+',
    default=[
        "jyut6ping3.chars.dict.yaml",
        # "jyut6ping3.words.dict.yaml",
        # "jyut6ping3.phrase.dict.yaml",
        # "jyut6ping3.lettered.dict.yaml",
        # "jyut6ping3.maps.dict.yaml",
    ]
)
args = parser.parse_args()


INITIALS = [
    "b", "p", "m", "f",
    "d", "t", "n", "l",
    "z", "c", "s",
    "g", "gw", "k", "kw", "ng",
    "h", "j", "w"
]
ASPIRATED_INITIALS = ['p', 't', 'c', 'k', 'kw']  # no `h`
NEGATIVE_TONES = [1, 2, 3]
POSITIVE_TONES = [4, 5, 6]
INITIALS_NEG2VL = { # negative tone -> voiceless initial
    'm': "mh",
    'n': "nh", 'l': "lh",
    'z': 'c',
    'g': 'k', "gw": "kw", "ng": '',
    'j': 'i', 'w': 'u'
}
INITIALS_POS2V = { # positive tone -> voiced initial
    'p': 'b', 'f': 'v',
    't': 'd',
    'z': 'j', 'c': 'j', 's': 'z',
    'k': 'g', "kw": "gw", '': "ng",
    'h': 'x', 'j': 'r'
}


def split_init_fin(init_fin):
    if len(init_fin) > 1 and init_fin[:2] in INITIALS:  # gw, kw, ng
        if "ng" == init_fin:
            return '', init_fin
        return init_fin[:2], init_fin[2:]
    if init_fin[0] in INITIALS:
        if "m" == init_fin:
            return '', init_fin
        return init_fin[0], init_fin[1:]
    return '', init_fin


def cvt_initial(init, tone):
    res = None
    if tone in NEGATIVE_TONES:
        res = INITIALS_NEG2VL[init] if init in INITIALS_NEG2VL else init
    else:
        assert tone in POSITIVE_TONES, tone
        res = INITIALS_POS2V[init] if init in INITIALS_POS2V else init
    if init in ASPIRATED_INITIALS:
        res = init + 'h'
    return res


def cvt_final(fin):
    return fin.replace("yu", 'y')


def cvt_tone(tone, fin):
    if fin[-1] in "ptk":
        return ''
    if tone in [1, 4]:  # flat
        return ''
    if tone in [2, 5]:  # up
        return 'q'
    assert tone in [3, 6], tone  # down
    return 's'


def jyut6ping3_to_rytphings(j6p3_code):
    match_obj = re.match(r"([a-z]+)([1-6])", j6p3_code)
    assert match_obj is not None, j6p3_code
    init_fin = match_obj.group(1)
    tone = int(match_obj.group(2))
    # print(init_fin, tone)
    init, fin = split_init_fin(init_fin)
    assert "" != fin, "{}, {}, {}, {}".format(j6p3_code, init, fin, tone)
    init2 = cvt_initial(init, tone)
    fin2 = cvt_final(fin)
    if 'i' == init2 == fin2[0] or 'u' == init2 == fin2[0]:
        init2 = ''
    tone2 = cvt_tone(tone, fin)
    return init2, fin2, tone2


for dict_f in args.dict_files:
    cvt_dict_f = '.'.join(["rytphings"] + dict_f.split('.')[1:])
    with open(osp.join(args.jyut6ping3_dir, dict_f), "r", encoding="utf-8") as f_j6p3, \
            open(cvt_dict_f, "w", encoding="utf-8") as f_rph:

        # heading
        f_rph.write("# {}\n\n---\nname: {}\nversion: \"{}\"\nsort: by_weight\n...\n\n".format(
            cvt_dict_f,
            '.'.join(cvt_dict_f.split('.')[:2]),
            time.strftime("%Y.%m.%d", time.localtime(time.time())),
        ))

        iter_line = iter(f_j6p3)
        # skip heading
        while True:
            line = next(iter_line).strip()
            if "..." == line:
                break

        _pre = (-1, -1)  # sampling
        for i, line in enumerate(iter_line):
            line = line.strip()
            if "" == line:
                continue
            code = line.split('\t')
            # print(code)
            if len(code) > 1:
                init, fin, tone = jyut6ping3_to_rytphings(code[1])
                if (init, tone) != _pre:  # sampling
                    print(code, "->", init + fin + tone)
                    _pre = (init, tone)
                code[1] = init + fin + tone
            f_rph.write('\t'.join(code) + '\n')

            # if i > 100:
            #     break # debug

    print("finish:", dict_f, "->", cvt_dict_f)
