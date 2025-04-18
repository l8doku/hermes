from jamdict import Jamdict

jam = Jamdict()


def extract_entry_info(entry, ru_only=True):
    full_entry_kanji = ""
    full_entry_kana = ""
    if not entry.senses:
        return None
    if entry.kanji_forms:
        full_entry_kanji = " ".join((f"({x.text})" for x in entry.kanji_forms))
    if entry.kana_forms:
        full_entry_kana = " ".join((f"[{x.text}]" for x in entry.kana_forms))

    if not entry.senses:
        return None

    found_rus = not ru_only
    idx = 0
    tmp = []
    for sense_index, sense in enumerate(entry.senses):
        if sense.gloss:
            if ru_only:
                if sense.gloss[0].lang != "rus":
                    continue
                else:
                    found_rus = True

        idx += 1
        tmp2 = []
        for i, x in enumerate(sense.gloss):
            if i > 3:
                break
            tmp2.append(f"{x.text}")

        if sense.pos:
            tmp.append(
                "{gloss} ({pos})".format(
                    gloss="\n".join(tmp2), pos=("(%s)" % "|".join(sense.pos))
                )
            )
        else:
            tmp.append("\n".join(tmp2))
    entries_together = "\n".join(tmp)

    
    final_text = (
        f"{full_entry_kanji}\n"
        f"{full_entry_kana}\n"
        f"{entries_together}\n"
    )

    if not found_rus:
        return None
    return final_text


def lookup(word):

    # t = MeCab.Tagger()
    # sentence = "太郎はこの本を女性に渡した。"
    # print(t.parse(sentence))

    fail_message = f"Ничего не найдено по запросу {word}"

    result = jam.lookup(word)
    if len(result.entries) == 0:
        return fail_message

    for entry in result.entries:
        result = extract_entry_info(entry, ru_only=True)
        if result:
            return result
    # no Russian results

    # restart iterator
    result = jam.lookup(word) 
    for entry in result.entries:
        result = extract_entry_info(entry, ru_only=False)
        if result:
            final = (
                "Не найдено результатов на русском языке. Найдены результаты на других языках:\n\n"
                f"{result}"
            )
            return final

    return fail_message
