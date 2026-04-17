class Question[T]:
    def unsafe_ask(
        self,
        patch_stdout: bool = False,
    ) -> T: ...
