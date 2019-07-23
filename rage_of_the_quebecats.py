import os

from lasercats import run_lots


# np.random.seed(10)

ANSWER = "LIVIDFELID"
WORKING_GRIDS = [[] for _ in ANSWER]
OUTPUT_DIR = "/Users/dfarhi/Desktop/LaserCats"

def output_if_puzzle_extracts_letter(room):
    path = room.paths[-1]
    path_idx = len(room.paths)
    letter = chr(len(path) + 64)
    end_location = path.cursor_location
    if end_location[1] == -1:
        answer_idx = end_location[0]
    elif end_location[1] == 5:
        answer_idx = end_location[0] + 5
    else:
        # Path ended due to horizontal wall. Forget about it.
        return False
    if ANSWER[answer_idx] == letter:
        print(
            "Made a path of difficulty {} which would put a {} at position {}".format(path.heuristic_breakin_score, letter,
                                                                                      answer_idx))
        WORKING_GRIDS[answer_idx].append((room, path_idx))
        room.dump_puzzle(os.path.join(OUTPUT_DIR, str(answer_idx)))
        return True
    return False



run_lots(10000, 12, output_if_puzzle_extracts_letter)

# g = Grid()
# g.display()
#
# # g.launch_laser()
# # g.launch_laser()
# # g.pretty_print_puzzle(2)
#
# g.launch_lotsa_lasers(10)
# g.pretty_print_puzzle(10)