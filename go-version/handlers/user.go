package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"

	"my-shop/models"
)

type UserHandler struct {
	DB        *gorm.DB
	JWTSecret string
}

func (h *UserHandler) Register(c *gin.Context) {
	var req struct {
		Username string `json:"username" binding:"required,min=3,max=50"`
		Password string `json:"password" binding:"required,min=6,max=100"`
		Email    string `json:"email"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	hash, _ := bcrypt.GenerateFromPassword([]byte(req.Password), 4)
	user := models.User{Username: req.Username, Password: string(hash), Email: req.Email}
	if err := h.DB.Create(&user).Error; err != nil {
		c.JSON(http.StatusConflict, gin.H{"error": "用户名已存在"})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"message": "注册成功", "user_id": user.ID})
}

func (h *UserHandler) Login(c *gin.Context) {
	var req struct {
		Username string `json:"username" binding:"required"`
		Password string `json:"password" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var user models.User
	if err := h.DB.Where("username = ?", req.Username).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "用户名或密码错误"})
		return
	}
	if err := bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(req.Password)); err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "用户名或密码错误"})
		return
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"user_id":  user.ID,
		"is_admin": user.IsAdmin,
		"exp":      time.Now().Add(72 * time.Hour).Unix(),
	})
	tokenStr, _ := token.SignedString([]byte(h.JWTSecret))

	c.JSON(http.StatusOK, gin.H{"token": tokenStr, "user_id": user.ID, "level": user.Level, "is_admin": user.IsAdmin})
}

func (h *UserHandler) Profile(c *gin.Context) {
	userID := c.GetUint("user_id")
	var user models.User
	if err := h.DB.First(&user, userID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "用户不存在"})
		return
	}
	c.JSON(http.StatusOK, user)
}

func (h *UserHandler) AddPoints(c *gin.Context) {
	userID := c.GetUint("user_id")
	var req struct {
		Points int `json:"points" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	h.DB.Model(&models.User{}).Where("id = ?", userID).UpdateColumn("points", gorm.Expr("points + ?", req.Points))
	c.JSON(http.StatusOK, gin.H{"message": "积分已更新"})
}
