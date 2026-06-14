package models

import "time"

type Cart struct {
	ID        uint       `gorm:"primaryKey" json:"id"`
	UserID    uint       `gorm:"uniqueIndex;not null" json:"user_id"`
	Items     []CartItem `gorm:"foreignKey:CartID" json:"items"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
}

type CartItem struct {
	ID        uint    `gorm:"primaryKey" json:"id"`
	CartID    uint    `gorm:"index;not null" json:"cart_id"`
	ProductID uint    `gorm:"not null" json:"product_id"`
	Product   Product `gorm:"foreignKey:ProductID" json:"product"`
	Quantity  int     `gorm:"not null;default:1" json:"quantity"`
}
