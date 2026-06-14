package models

import "time"

type ProductCategory struct {
	ID          uint   `gorm:"primaryKey" json:"id"`
	Name        string `gorm:"size:100;not null" json:"name"`
	Description string `gorm:"size:500" json:"description"`
	SortOrder   int    `gorm:"default:0" json:"sort_order"`
	CreatedAt   time.Time `json:"created_at"`
}
