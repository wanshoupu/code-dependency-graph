import json
import re
from enum import Enum


class RefType(Enum):
    INHERITANCE = 1
    COMPOSITION = 2
    FUNCTION = 3


class SourceType(Enum):
    HEADER = re.compile(r'h|hpp')
    CPP = re.compile(r'c|cc|cpp|c\+\+')

    @staticmethod
    def parseval(symbol):
        for item in list(SourceType):
            if re.fullmatch(item.value, symbol):
                return item


class TypeClassifier(Enum):
    ENUM = 'enum'
    STRUCT = 'struct'
    CLASS = 'class'

    @staticmethod
    def parseval(symbol):
        for item in list(TypeClassifier):
            if item.value == symbol:
                return item


class Node:
    def __init__(self, name, classifier: TypeClassifier, sourceName, sourceType: SourceType) -> None:
        # class name
        self.name = name

        self.sourceType = sourceType
        # file basename without extension
        self.sourceName = sourceName
        self.classifier = classifier

    def __hash__(self) -> int:
        return hash(self.name) ^ hash(self.sourceType) ^ hash(self.sourceName) ^ hash(self.classifier)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False

        return (self.name == other.name
                and self.sourceType == other.sourceType
                and self.sourceName == other.sourceName
                and self.classifier == other.classifier)

    def __str__(self) -> str:
        return self.name


class NodeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Node):
            return {"name": obj.name, "classifier": obj.classifier.name, "sourceName": obj.sourceName, "sourceType": obj.sourceType.name}
        return json.JSONEncoder.default(self, obj)


class NodeDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct):
        if 'name' in dct and 'classifier' in dct and 'sourceName' in dct and 'sourceType' in dct:
            return Node(dct['name'], TypeClassifier[dct['classifier']], dct['sourceName'], SourceType[dct['sourceType']])
        return dct


class EdgeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Edge):
            caller = json.dumps(obj.caller, cls=NodeEncoder)
            callee = json.dumps(obj.callee, cls=NodeEncoder)
            return {"caller": caller, "callee": callee, "refType": obj.refType.name}
        return json.JSONEncoder.default(self, obj)


class EdgeDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct):
        if 'caller' in dct and 'callee' in dct and 'refType' in dct:
            caller = json.loads(dct['caller'], cls=NodeDecoder)
            callee = json.loads(dct['callee'], cls=NodeDecoder)
            return Edge(caller, callee, RefType[dct['refType']])
        return dct


class Edge:
    def __init__(self, caller: Node, callee: Node, refType: RefType) -> None:
        self.callee = callee
        self.caller = caller
        self.refType = refType

    def __hash__(self) -> int:
        return hash(self.caller) ^ hash(self.callee) ^ hash(self.refType)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False

        return (self.caller == other.sourceName
                and self.callee == other.sourceType
                and self.refType == other.name)

    def __str__(self) -> str:
        return f'{self.caller} -> {self.callee}'


if __name__ == '__main__':
    tc = TypeClassifier.parseval('struct')
    print(tc)
    st = SourceType.parseval('c++')
    print(st)
    abc = Node('abc', TypeClassifier.ENUM, 'foo', SourceType.HEADER)
    abc_json = json.dumps(abc, cls=NodeEncoder)
    resurrected_abc = json.loads(abc_json, cls=NodeDecoder)
    print(f'original: {abc}\njson: {abc_json}\nresurrected: {resurrected_abc}')

    foo = Node('Foo', TypeClassifier.CLASS, 'bar', SourceType.CPP)
    edge = Edge(foo, abc, RefType.COMPOSITION)
    edge_json = json.dumps(edge, cls=EdgeEncoder)
    resurrected_edge = json.loads(edge_json, cls=EdgeDecoder)
    print(f'original: {edge}\njson: {edge_json}\n resurrected: {resurrected_edge}')
