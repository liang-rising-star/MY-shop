package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type AdminHandler struct {
	DB *gorm.DB
}

func (h *AdminHandler) ListUsers(c *gin.Context) {
	var users []models.User
	h.DB.Order("id desc").Find(&users)
	for i := range users {
		users[i].Password = ""
	}
	c.JSON(http.StatusOK, users)
}

type AppSettings struct {
	ShopName      string `json:"shop_name"`
	ShopDesc      string `json:"shop_desc"`
	PageSize      int    `json:"page_size"`
	AllowRegister bool   `json:"allow_register"`
}

var CurrentSettings = AppSettings{
	ShopName: "MY-Shop", ShopDesc: "穿越维度的购物体验",
	PageSize: 20, AllowRegister: true,
}

func (h *AdminHandler) GetSettings(c *gin.Context) {
	c.JSON(http.StatusOK, CurrentSettings)
}

func (h *AdminHandler) SaveSettings(c *gin.Context) {
	var s AppSettings
	if err := c.ShouldBindJSON(&s); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	CurrentSettings = s
	c.JSON(http.StatusOK, gin.H{"message": "设置已保存"})
}
