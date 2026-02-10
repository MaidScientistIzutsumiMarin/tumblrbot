class Question[T]:
    def ask(
        self,
        patch_stdout: bool = False,
        kbi_msg: str = ...,
    ) -> T: ...
