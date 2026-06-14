package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"

	"my-shop/config"
	"my-shop/database"
	"my-shop/routes"
)

var mimeTypes = map[string]string{
	".css":  "text/css; charset=utf-8",
	".js":   "application/javascript; charset=utf-8",
	".html": "text/html; charset=utf-8",
	".png":  "image/png",
	".jpg":  "image/jpeg",
	".jpeg": "image/jpeg",
	".gif":  "image/gif",
	".svg":  "image/svg+xml",
	".ico":  "image/x-icon",
	".json": "application/json",
}

func main() {
	godotenv.Load()
	cfg := config.Load()

	if err := database.Init(cfg.DBPath); err != nil {
		log.Fatalf("failed to init database: %v", err)
	}

	r := gin.Default()

	routes.Setup(r, database.DB, cfg.JWTSecret)

	r.GET("/admin", func(c *gin.Context) {
		c.Header("Content-Type", "text/html; charset=utf-8")
		c.File("./static/admin.html")
	})

	r.NoRoute(func(c *gin.Context) {
		if strings.HasPrefix(c.Request.URL.Path, "/api/") {
			c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
			return
		}
		localPath := "." + c.Request.URL.Path
		if info, err := os.Stat(localPath); err == nil && !info.IsDir() {
			ext := filepath.Ext(localPath)
			if mime, ok := mimeTypes[ext]; ok {
				c.Header("Content-Type", mime)
			}
			c.File(localPath)
			return
		}
		c.File("./static/index.html")
	})

	r.Run(fmt.Sprintf(":%d", cfg.Port))
}
