package config

import (
	"os"
	"strconv"
)

type Config struct {
	Port      int
	DBPath    string
	JWTSecret string
}

func Load() *Config {
	port, _ := strconv.Atoi(getEnv("PORT", "8080"))
	return &Config{
		Port:      port,
		DBPath:    getEnv("DB_PATH", "shop.db"),
		JWTSecret: getEnv("JWT_SECRET", "my-shop-secret-key"),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
