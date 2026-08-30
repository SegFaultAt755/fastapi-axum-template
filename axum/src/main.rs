use std::{env, net::SocketAddr};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, put},
    Json, Router,
};
use deadpool_postgres::{Manager, ManagerConfig, Pool, RecyclingMethod, Runtime};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use tokio_postgres::NoTls;

const DEFAULT_ITERATIONS: u32 = 2_000;
const MAX_ITERATIONS: u32 = 100_000;
const DATABASE_POOL_SIZE: usize = 10;

#[derive(Clone)]
struct AppState {
    pool: Pool,
}

#[derive(Serialize)]
struct User {
    id: i32,
    name: String,
    age: i32,
    email: String,
    is_male: bool,
}

struct AppError {
    status: StatusCode,
    message: String,
}

impl AppError {
    fn internal(error: impl std::fmt::Display) -> Self {
        Self {
            status: StatusCode::INTERNAL_SERVER_ERROR,
            message: error.to_string(),
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        (self.status, Json(json!({ "detail": self.message }))).into_response()
    }
}

#[derive(Deserialize)]
struct ComputeQuery {
    #[serde(default = "default_iterations")]
    iterations: u32,
    #[serde(default = "default_data")]
    data: String,
}

#[derive(Deserialize)]
struct IterationsQuery {
    #[serde(default = "default_iterations")]
    iterations: u32,
}

fn default_iterations() -> u32 {
    DEFAULT_ITERATIONS
}

fn default_data() -> String {
    "benchmark-payload".to_owned()
}

fn validate_iterations(iterations: u32) -> Result<u32, AppError> {
    if (1..=MAX_ITERATIONS).contains(&iterations) {
        Ok(iterations)
    } else {
        Err(AppError {
            status: StatusCode::UNPROCESSABLE_ENTITY,
            message: "iterations must be between 1 and 100000".to_owned(),
        })
    }
}

fn compute_digest(data: &str, iterations: u32) -> String {
    // The benchmark intentionally re-hashes the previous result so each request creates
    // a predictable CPU-heavy workload without any data-dependent branching.
    let payload = data.as_bytes();
    let mut digest = payload.to_vec();

    for _ in 0..iterations {
        let mut hasher = Sha256::new();
        hasher.update(&digest);
        hasher.update(payload);
        digest = hasher.finalize().to_vec();
    }

    hex::encode(digest)
}

async fn read_user(pool: &Pool, user_id: i32) -> Result<Option<User>, AppError> {
    let client = pool.get().await.map_err(AppError::internal)?;
    let row = client
        .query_opt(
            "SELECT id, name, age, email, is_male FROM users WHERE id = $1",
            &[&user_id],
        )
        .await
        .map_err(AppError::internal)?;
    Ok(row.map(user_from_row))
}

fn user_from_row(row: tokio_postgres::Row) -> User {
    User {
        id: row.get("id"),
        name: row.get("name"),
        age: row.get("age"),
        email: row.get("email"),
        is_male: row.get("is_male"),
    }
}

async fn root() -> Json<&'static str> {
    Json("Hello, World!")
}

async fn get_user(
    State(state): State<AppState>,
    Path(user_id): Path<i32>,
) -> Result<Response, AppError> {
    match read_user(&state.pool, user_id).await? {
        Some(user) => Ok(Json(user).into_response()),
        None => Err(AppError {
            status: StatusCode::NOT_FOUND,
            message: "User not found".to_owned(),
        }),
    }
}

async fn update_user_age(
    State(state): State<AppState>,
    Path((user_id, age)): Path<(i32, i32)>,
) -> Result<Response, AppError> {
    if !(0..=150).contains(&age) {
        return Err(AppError {
            status: StatusCode::UNPROCESSABLE_ENTITY,
            message: "age must be between 0 and 150".to_owned(),
        });
    }

    let client = state.pool.get().await.map_err(AppError::internal)?;
    let row = client
        .query_opt(
            "UPDATE users SET age = $1 WHERE id = $2 RETURNING id, name, age, email, is_male",
            &[&age, &user_id],
        )
        .await
        .map_err(AppError::internal)?;

    match row {
        Some(row) => Ok(Json(user_from_row(row)).into_response()),
        None => Err(AppError {
            status: StatusCode::NOT_FOUND,
            message: "User not found".to_owned(),
        }),
    }
}

async fn compute_without_database(
    Query(query): Query<ComputeQuery>,
) -> Result<Json<Value>, AppError> {
    let iterations = validate_iterations(query.iterations)?;
    Ok(Json(json!({
        "digest": compute_digest(&query.data, iterations),
        "iterations": iterations,
    })))
}

async fn compute_with_database(
    State(state): State<AppState>,
    Path(user_id): Path<i32>,
    Query(query): Query<IterationsQuery>,
) -> Result<Json<Value>, AppError> {
    let iterations = validate_iterations(query.iterations)?;
    let user = read_user(&state.pool, user_id)
        .await?
        .ok_or_else(|| AppError {
            status: StatusCode::NOT_FOUND,
            message: "User not found".to_owned(),
        })?;

    let is_male = if user.is_male { "True" } else { "False" };
    let data = format!(
        "{}|{}|{}|{}|{}",
        user.id, user.name, user.age, user.email, is_male
    );

    Ok(Json(json!({
        "digest": compute_digest(&data, iterations),
        "iterations": iterations,
        "user_id": user_id,
    })))
}

fn build_app_router(state: AppState) -> Router {
    Router::new()
        .route("/", get(root))
        .route("/user/{user_id}", get(get_user))
        .route("/user/{user_id}/age/{age}", put(update_user_age))
        .route("/compute", get(compute_without_database))
        .route("/compute-db/{user_id}", get(compute_with_database))
        .with_state(state)
}

fn build_pool() -> Result<Pool, Box<dyn std::error::Error>> {
    // Centralize the Postgres pool configuration so runtime startup stays readable and
    // keeps the default connection string in a single place.
    let database_url = env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://app_user:app_password@localhost:5432/app_db".to_owned());
    let config = database_url.parse()?;
    let manager = Manager::from_config(
        config,
        NoTls,
        ManagerConfig {
            recycling_method: RecyclingMethod::Fast,
        },
    );

    Ok(Pool::builder(manager)
        .max_size(DATABASE_POOL_SIZE)
        .runtime(Runtime::Tokio1)
        .build()?)
}

#[tokio::main(flavor = "multi_thread", worker_threads = 5)]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let pool = build_pool()?;
    let state = AppState { pool };
    let router = build_app_router(state);
    let address: SocketAddr = "0.0.0.0:8001".parse()?;
    let listener = tokio::net::TcpListener::bind(address).await?;
    axum::serve(listener, router).await?;
    Ok(())
}
