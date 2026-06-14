package routes

import (
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/handlers"
	"my-shop/middleware"
)

func Setup(r *gin.Engine, db *gorm.DB, jwtSecret string) {
	uh := &handlers.UserHandler{DB: db, JWTSecret: jwtSecret}
	ch := &handlers.CategoryHandler{DB: db}
	ph := &handlers.ProductHandler{DB: db}
	kh := &handlers.CardKeyHandler{DB: db}
	cp := &handlers.CouponHandler{DB: db}
	oh := &handlers.OrderHandler{DB: db}
	rh := &handlers.ReviewHandler{DB: db}
	sh := &handlers.SetupHandler{DB: db}
	ah := &handlers.AdminHandler{DB: db}

	api := r.Group("/api")

	auth := api.Group("")
	auth.Use(middleware.AuthMiddleware(jwtSecret))

	// Setup
	api.GET("/setup/status", sh.Status)
	api.POST("/setup/init", sh.Init)

	// Public
	api.POST("/register", uh.Register)
	api.POST("/login", uh.Login)

	api.GET("/products", ph.List)
	api.GET("/products/:id", ph.Get)
	api.GET("/categories", ch.List)
	api.GET("/reviews", rh.List)
	api.POST("/coupon/validate", cp.Validate)

	// User
	auth.GET("/profile", uh.Profile)
	auth.POST("/points", uh.AddPoints)

	// Cart / Order
	auth.POST("/orders", oh.Checkout)
	auth.GET("/orders", oh.List)
	auth.GET("/orders/:id", oh.Get)

	// Coupons
	auth.POST("/coupon/claim", cp.Claim)
	auth.GET("/coupons/mine", cp.MyCoupons)

	// Reviews
	auth.POST("/reviews", rh.Create)

	// Admin
	admin := auth.Group("/admin")
	admin.Use(middleware.AdminMiddleware())

	admin.GET("/orders", oh.ListAll)

	admin.POST("/categories", ch.Create)
	admin.PUT("/categories/:id", ch.Update)
	admin.DELETE("/categories/:id", ch.Delete)

	admin.POST("/products", ph.Create)
	admin.PUT("/products/:id", ph.Update)
	admin.DELETE("/products/:id", ph.Delete)
	admin.PUT("/products/:id/blindbox", ph.UpdateBlindBoxPool)

	admin.POST("/cardkeys/import", kh.Import)
	admin.GET("/cardkeys", kh.List)
	admin.DELETE("/cardkeys/:id", kh.Delete)
	admin.DELETE("/cardkeys/product/:id", kh.DeleteByProduct)
	admin.GET("/cardkeys/export", kh.ExportSold)

	admin.POST("/coupons", cp.Create)
	admin.GET("/coupons", cp.List)
	admin.DELETE("/coupons/:id", cp.Delete)

	admin.DELETE("/reviews/:id", rh.Delete)

	admin.GET("/users", ah.ListUsers)
	admin.GET("/settings", ah.GetSettings)
	admin.POST("/settings", ah.SaveSettings)
}
