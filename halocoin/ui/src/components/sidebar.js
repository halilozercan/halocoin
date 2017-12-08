import React, { Component } from 'react';

class MSidebar extends Component {
  render() {
    return (
      <div className="sidebar" data-color="purple" data-image="{{ url_for('.static', filename='img/sidebar-1.jpg') }}">
				<div className="logo">
					<a href="http://alkanlab.org" className="simple-text">
						Halocoin
					</a>
				</div>
				<div className="sidebar-wrapper">
					<ul className="nav">
						<li className="active">
							<a href="#">
								<i className="material-icons">dashboard</i>
								<p>Dashboard</p>
							</a>
						</li>
						<li>
							<a href="#">
							<i className="material-icons">explore</i>
							<p>Block Explorer</p>
						</a>
						</li>
					</ul>
				</div>
			</div>
    );
  }
}

export default MSidebar;
