from enum import Enum
from typing import List

class OutputFlag(Enum):
    Empty = 0
    Debug = 1
    Info = 2
    Skip = 3
    Succeed = 4
    Warn = 5
    Abort = 6
    Error = 7
    Fatal = 8
    
class Output:
    def __init__(self, flag: OutputFlag = OutputFlag.Empty, content: str = ""):
        self.flag = flag
        self.content = content
    
    def ToStr(self, showFlag: bool = True) -> str:
        return f'{self.flag.name}: {self.content}' if showFlag else f'{self.content}'
    
    def __str__(self):
        return self.ToStr()

    def __add__(self, other):
        if isinstance(other, Output):
            return Outputs([self, other])
        elif isinstance(other, Outputs):
            return Outputs([self] + other.outputs)
        raise TypeError(f'Type [Output] Cannot add with Type [{type(other)}]')
    
    def __bool__(self):
        return self.flag.value <= OutputFlag.Warn.value

class Outputs:
    #outputs:List[Output] = []
    
    def __init__(self, outputs: List[Output] = None, showFlag: bool = True):
        self.outputs = outputs or []
        self.showFlag = showFlag
    
    @staticmethod
    def FromStr(flag: OutputFlag, content: str):
        return Outputs([Output(flag, content)])
    
    def append(self, flag: OutputFlag, content: str) -> None:
        self.outputs.append(Output(flag, content))
    
    @property
    def Result(self) -> OutputFlag:
        if len(self.outputs) == 0:
            return OutputFlag.Empty
        return OutputFlag(max(x.flag.value for x in self.outputs))
    
    @property
    def ResultStr(self) -> str:
        return self.Result.name
    
    def ToStr(self, showFlag: bool = None, sep: str = None) -> str:
        if showFlag is None:
            showFlag = self.showFlag
        if len(self.outputs) == 0 or all(x.flag == OutputFlag.Empty for x in self.outputs):
            return ""
        if len({x.flag for x in self.outputs}) == 1:
            sep = sep or " "
            x = f'{self.outputs[0].flag.name}: '
            y = f'{sep.join([x.content for x in self.outputs])}'
            return f'{x if showFlag else ""}{y}'            
        sep = sep or "\n"
        return sep.join(x.ToStr(showFlag) for x in self.outputs if x.flag != OutputFlag.Empty)

    def __str__(self):
        return self.ToStr()
    
    def __add__(self, other):
        if isinstance(other, Output):
            return Outputs(self.outputs + [other])
        elif isinstance(other, Outputs):
            return Outputs(self.outputs + other.outputs)
        raise TypeError(f'Type [Outputs] Cannot add with Type [{type(other)}]')
    
    def __iadd__(self, other):
        if isinstance(other, Output):
            self.outputs.append(other)
            return self
        elif isinstance(other, Outputs):
            self.outputs += other.outputs
            return self
        raise TypeError(f'Type [Outputs] Cannot add with Type [{type(other)}]')

    def __bool__(self):
        if len(self.outputs) == 0:
            return True
        return max(x.flag.value for x in self.outputs) <= OutputFlag.Warn.value
    
if __name__ == "__main__":
    ...
    # def MyTestFunc() -> Outputs:
    #     return Outputs([Output(OutputFlag.Skip, "11"), Output(OutputFlag.Warn, "22"), Output(OutputFlag.Succeed, "33")])
        
    # res = MyTestFunc()
    # print(res)
    
