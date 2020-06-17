def adjacent(row, col):
    yield row - 1, col - 1
    yield row, col - 1
    yield row + 1, col - 1
    yield row - 1, col
    yield row + 1, col
    yield row - 1, col + 1
    yield row, col + 1
    yield row + 1, col + 1

def get_board(board_detail):
    board = []
    for each_row in board_detail:
        row = list(each_row)
        board.append(row)
    return board

def get_row(board):
    return len(board)

def get_column(board):
    return len(board[0])

def get_mines(board, marker):
    mines = 0
    for row in range(0, get_row(board)):
        for col in range(0, get_column(board)):
            if board[row][col] == '9':
                mines += 1
                marker[row][col] = True
    return mines

def get_openings(board, marker):
    openings = 0
    rows = get_row(board)
    cols = get_column(board)
    for row in range(0, rows):
        for col in range(0, cols):
            if board[row][col] == '0' and not marker[row][col]:
                openings += 1
                marker[row][col] = True
                stack = [('0', row, col)]
                while len(stack) > 0:
                    cur_num, cur_row, cur_col = stack.pop()
                    marker[cur_row][cur_col] = True
                    # open again if find an opening
                    if cur_num == '0': 
                        for each_coord in adjacent(cur_row, cur_col):
                            ready_row, ready_col = each_coord
                            if 0 <= ready_row < rows and 0 <= ready_col < cols and not marker[ready_row][ready_col]:
                                ready_num = board[ready_row][ready_col]
                                stack.append((ready_num, ready_row, ready_col))
                                marker[ready_row][ready_col] = True
    return openings

def get_isolated_bv(board, marker):
    isolated_bv = 0
    for row in range(0, get_row(board)):
        for col in range(0, get_column(board)):
            if not marker[row][col]:
                isolated_bv += 1
    return isolated_bv

def get_islands(board, marker):
    islands = 0
    rows = get_row(board)
    cols = get_column(board)
    for row in range(0, rows):
        for col in range(0, cols):
            if not marker[row][col]:
                islands += 1
                marker[row][col] = True
                stack = [(row, col)]
                while len(stack) > 0:
                    cur_row, cur_col = stack.pop()
                    marker[cur_row][cur_col] = True
                    # search again if find an adjacent isolated bv 
                    for each_coord in adjacent(cur_row, cur_col):
                        ready_row, ready_col = each_coord
                        if 0 <= ready_row < rows and 0 <= ready_col < cols and not marker[ready_row][ready_col]:
                            stack.append((ready_row, ready_col))
                            marker[ready_row][ready_col] = True
    return islands

def get_action(action_detail):
    split_action = []
    for each_action in action_detail:
        operation, row, column, current_time = each_action.split(':')
        split_action.append([int(operation), int(row), int(column), int(current_time)])

    current = 0
    while current < len(split_action) - 2:
        if split_action[current][0] == 2 and split_action[current + 1][0] == 3:
            if split_action[current + 2][0] == 1 and split_action[current + 1][1] == split_action[current + 2][1] and split_action[current + 1][2] == split_action[current + 2][2] \
                and split_action[current][1] == split_action[current + 2][1] and split_action[current][2] == split_action[current + 2][2]:
                # this indicates the action is valid
                split_action[current + 2][0] = 4
                current += 3
            else:
                # this indicates the action is invalid
                split_action[current][0] = -1
                split_action[current + 1][0] = -1
                current += 2  
        else:
            current += 1
    return split_action

def get_board_result(board):
    result = {}
    result['row'] = get_row(board)
    result['column'] = get_column(board)

    marker = [[False for col in range(0, get_column(board))] for row in range(0, get_row(board))]
    result['mines'] = get_mines(board, marker)
    result['op'] = get_openings(board, marker)
    result['bv'] = result['op'] + get_isolated_bv(board, marker)
    result['is'] = get_islands(board, marker)
    return result    

