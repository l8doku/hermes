import json
from functools import reduce


def getRomajiToKanaTree():
    with open("bot/romaji_to_kana_tree.json") as f:
        return json.load(f)

kana_tree = getRomajiToKanaTree()


def applyMapping(string, mapping):
    root = mapping

    def nextSubtree(tree, nextChar):
        subtree = tree[nextChar]
        if subtree == None:
            return None

        # if the next child node does not have a node value, set its node value to the input
        result = {"": tree[""] + nextChar}
        result.update(tree[nextChar])
        return result

    def newChunk(remaining: str, currentCursor):
        # start parsing a new chunk
        firstChar = remaining[0]
        nextTree = {"": firstChar}
        nextTree.update(root[firstChar])
        return parse(
            nextTree,
            remaining[1:],
            currentCursor,
            currentCursor + 1,
        )

    def parse(tree, remaining, lastCursor, currentCursor):
        if not remaining:
            if len(tree) == 1:
                # nothing more to consume, just commit the last chunk and return it
                # so as to not have an empty element at the end of the result
                if tree[""]:
                    return [[lastCursor, currentCursor, tree[""]]]
                else:
                    return []

            # if we don't want to convert the ending, because there are still possible continuations
            # return null as the final node value
            return [[lastCursor, currentCursor, None]]

        if len(tree) == 1:
            return [[lastCursor, currentCursor, tree[""]]] + newChunk(remaining, currentCursor)

        subtree = nextSubtree(tree, remaining[0])

        if subtree == None:
            return [[lastCursor, currentCursor, tree[""]]] + newChunk(remaining, currentCursor)

        # continue current branch
        return parse(subtree, remaining[1:], lastCursor, currentCursor + 1)

    return newChunk(string, 0)



def toKana(roma_input):
    conversion_map = kana_tree

    try:
        converted_kana = applyMapping(roma_input.lower(), conversion_map)
    except KeyError:
        return None

    converted_final = []
    for kanaToken in converted_kana:
        start, end, kana = kanaToken
        converted_final.append(kana)
    return "".join(converted_final)

