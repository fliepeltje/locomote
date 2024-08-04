from difflib import ndiff

def get_line_diff(seq_a: str, seq_b: str):
    return [x for x in ndiff(seq_a.split(" "), seq_b.split(" ")) if not x.startswith("?")]

def get_doc_diff(seq_a: str, seq_b: str):
    return [x for x in ndiff(seq_a.splitlines(keepends=True), seq_b.splitlines(keepends=True)) if not x.startswith("?")]

class DeleteChar(int):
    pass

class DeleteSegment(tuple[int, str]):

    @classmethod
    def from_diff(cls, diff: list[str], base_idx: int) -> list["DeleteSegment"]:
        segments = []
        idx = base_idx
        for item in diff:
            if item.startswith(" "):
                idx += len(item[2:]) + 1
            elif item.startswith("-"):
                segments.append(cls((idx, item[2:])))
                idx += len(item[2:]) + 1
        return segments


    def into_chars(self) -> list[DeleteChar]:
        index, word = self
        return sorted([
            DeleteChar(index+i) for i in range(len(word))
        ], reverse=True)
    
    def __repr__(self) -> str:
        return f"DELETE: START AT: {self[0]}, SEGMENT: {self[1]}"
    
    def as_add(self) -> "AddSegment":
        return AddSegment(self)

class AddChar(tuple[int, str]):
    pass

class AddSegment(tuple[int, str]):

    def __lt__(self, other) -> bool:
        if isinstance(other, DeleteSegment):
            return False
        else:
            return self[0] < other[0]

    @classmethod
    def from_diff(cls, diff: list[str], base_idx: int) -> list["AddSegment"]:
        segments = []
        idx = base_idx
        for item in diff:
            if item.startswith(" "):
                idx += len(item[2:]) + 1
            elif item.startswith("+"):
                segments.append(cls((idx, item[2:])))
                idx += len(item[2:]) + 1
        return segments
    
    def into_chars(self) -> list[AddChar]:
        index, word = self
        return [AddChar((index+i, char)) for i, char in enumerate(word)]
    
    def as_delete(self) -> "DeleteSegment":
        return DeleteSegment(self)
    
    def __repr__(self) -> str:
        return f"ADD: START AT: {self[0]}, SEGMENT: {self[1]}"


class InputSequence(str):
    _history = []
    _iterations = []
    
    def __add__(self, update) -> "InputSequence":
        if isinstance(update, list):
            for item in update:
                self += item
            return self
        elif isinstance(update, DeleteChar):
            # todo: store as img
            seq =  InputSequence(self[:update] + self[update+1:])
            self._iterations.append(str(seq))
            return seq
        elif isinstance(update, DeleteSegment):
            # self += update.into_chars()
            self._history.append(update)
            return self
        elif isinstance(update, AddChar):
            # todo: store as img
            index, char = update
            # self.history.append(update)
            seq = InputSequence(self[:index] + char + self[index:])
            self._iterations.append(str(seq))
            return seq
        elif isinstance(update, AddSegment):
            last_update = self._history[-1] if self._history else None
            if isinstance(last_update, DeleteSegment) and last_update[0] == update[0]:
                del_segment = self._history.pop()
                segment_diff = get_line_diff(del_segment[1], update[1])
                delete_segments = DeleteSegment.from_diff(segment_diff, update[0])
                add_segments = AddSegment.from_diff(segment_diff, update[0])
                for del_segment in delete_segments:
                    if del_segment.as_add() not in add_segments:
                        self._history.append(del_segment)
                for add_segment in add_segments:
                    if add_segment.as_delete() not in delete_segments:
                        self._history.append(add_segment)
                return self
            self._history.append(update)
            return self

        return InputSequence(super().__add__(update))
    
    @property
    def history(self):
        return list(self._history)

    @property
    def iterations(self):
        return list(self._iterations)

def create_iterated_Sequence(seq: str, updates: list[AddSegment | DeleteSegment]) -> str:
    seqq = InputSequence(seq)
    for item in updates:
        seqq += item.into_chars()
    return seqq
    