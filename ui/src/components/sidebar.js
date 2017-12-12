import React, { Component } from 'react';

class MSidebar extends Component {
  render() {
    return (
      <div className="sidebar" data-color="purple" data-image="{{ url_for('.static', filename='img/sidebar-1.jpg') }}">
        <div className="logo">
          <a href="http://alkanlab.org" className="simple-text">
            Coinami
          </a>
        </div>
        <div className="sidebar-wrapper">
          <ul className="nav">
            {Object.keys(this.props.pages).map((key, index) => {
            	let _class = (key === this.props.currentPage) ? "active":"";
            	return <li key={key} className={_class} onClick={() => {this.props.pageChange(key)} }>
			              <a>
			                <i className="material-icons">{this.props.pages[key]}</i>
			                <p>{key}</p>
			              </a>
			            </li>;
            })}
          </ul>
        </div>
      </div>
    );
  }
}

export default MSidebar;
