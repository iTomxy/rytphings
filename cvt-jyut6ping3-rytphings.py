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
    'b': 'p', 'm': "mh",
    'd': 't', 'n': "nh", 'l': "lh",
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
# skip corner cases & deal with them later in `rytphings.mod.dict.yaml`
SKIP = set([
    r"哦", r"呀"
])


def split_init_fin(init_fin):
    if len(init_fin) >= 2 and init_fin[:2] in INITIALS:  # gw, kw, ng
        if "ng" == init_fin:
            return '', init_fin
        return init_fin[:2], init_fin[2:]
    if init_fin[0] in INITIALS:
        if "m" == init_fin:
            return '', init_fin
        return init_fin[0], init_fin[1:]
    return '', init_fin


def cvt_initial(init, fin, tone):
    init2 = None
    if tone in NEGATIVE_TONES:
        init2 = INITIALS_NEG2VL[init] if init in INITIALS_NEG2VL else init
    else:
        assert tone in POSITIVE_TONES, str(tone)
        if '' == init and fin in ["ng", 'm']:  # avoid "ngng", "ngm"
            init2 = init
        else:
            init2 = INITIALS_POS2V[init] if init in INITIALS_POS2V else init
    if init in ASPIRATED_INITIALS:
        init2 += 'h'
    return init2


def cvt_final(fin, tone):
    fin2 = fin.replace("yu", 'y').replace("eoi", "eoy")
    # distinguish upper & lower negative chekced tone by ending consonant
    if 3 == tone and fin[-1] in "ptk":
        fin2 = fin2[:-1] + {'p': 'b', 't': 'd', 'k': 'g'}[fin[-1]]
    return fin2


def cvt_tone(tone, fin):
    if fin[-1] in "ptkbd" or 'g' == fin[-1] and "ng" != fin[-2:]:  # checked
        if tone in [2, 5]:  # support modified raising tone
            return 'q'
        else:
            return ''
    if tone in [1, 4]:  # even
        return ''
    if tone in [2, 5]:  # raising
        return 'q'
    assert tone in [3, 6], str(tone)  # falling
    return 's'


def jyut6ping3_to_rytphings(j6p3_spell):
    match_obj = re.match(r"([a-z]+)([1-6])", j6p3_spell)
    assert match_obj is not None, j6p3_spell
    init_fin = match_obj.group(1)
    tone = int(match_obj.group(2))
    # print(init_fin, tone)
    init, fin = split_init_fin(init_fin)
    assert "" != fin, "{}, {}, {}, {}".format(j6p3_spell, init, fin, tone)
    init2 = cvt_initial(init, fin, tone)
    fin2 = cvt_final(fin, tone)
    if 'i' == init2 == fin2[0] or 'u' == init2 == fin2[0]:
        init2 = ''
    tone2 = cvt_tone(tone, fin)

    ret = [(init2, fin2, tone2)]
    # if 6 == tone and fin2[-1] in "ptk": # positive checked tone
    #     # e.g. 別 bit = bid != 必 pit != 憋 pid
    #     fin3 = fin2[:-1] + {'p': 'b', 't': 'd', 'k': 'g'}[fin2[-1]]
    #     ret.append([init2, fin3, tone2])

    return ret


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

        _pre = (-1, -1, -1)  # sampling
        for i, line in enumerate(iter_line):
            line = line.strip()
            if "" == line:
                continue
            spell = line.split('\t')
            # print(spell)
            if spell[0] in SKIP:
                print("skip:", spell)
                continue
            if len(spell) > 1: # defined spelling
                for init, fin, tone in jyut6ping3_to_rytphings(spell[1]):
                    if (init, fin, tone) != _pre:  # sampling
                        print(spell, "->", init + fin + tone)
                        _pre = (init, fin, tone)
                    spell[1] = init + fin + tone
                    f_rph.write('\t'.join(spell) + '\n')
            else: # only phrase, no specified spelling
                f_rph.write('\t'.join(spell) + '\n')

            # if i > 100:
            #     break # debug

    print("finish:", dict_f, "->", cvt_dict_f)
