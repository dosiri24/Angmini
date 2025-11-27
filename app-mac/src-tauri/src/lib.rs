// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

/// "항상 위에" 토글 명령
/// Why: 사용자가 창을 항상 다른 창 위에 표시할지 선택 가능
#[tauri::command]
fn set_always_on_top(window: tauri::Window, enabled: bool) -> Result<(), String> {
    window
        .set_always_on_top(enabled)
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// 현재 "항상 위에" 상태 조회
#[tauri::command]
fn is_always_on_top(window: tauri::Window) -> Result<bool, String> {
    window
        .is_always_on_top()
        .map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_http::init())
        .invoke_handler(tauri::generate_handler![greet, set_always_on_top, is_always_on_top])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
