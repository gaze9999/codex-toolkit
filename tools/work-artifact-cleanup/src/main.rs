use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let code = work_artifact_cleanup::run(&args, &mut std::io::stdout(), &mut std::io::stderr());
    ExitCode::from(code as u8)
}
