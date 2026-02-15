class Question[T]:
    def ask(
        self,
        patch_stdout: bool = False,
        kbi_msg: str = ...,
    ) -> T | None: ...
    def unsafe_ask(
        self,
        patch_stdout: bool = False,
    ) -> T: ...
